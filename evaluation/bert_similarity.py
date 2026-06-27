import json
import os
import math
import time
import warnings
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime
from scipy import stats
warnings.filterwarnings("ignore")
_CASE_SET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "training", "data", "fine_tuning_dialogue_dataset.json"
)
_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "training", "evaluation_results"
)
MODEL_CONFIGS = {
    "bert-base-chinese": {
        "name": "bert-base-chinese",
        "type": "BERT",
        "layers": 12,
        "hidden_size": 768,
        "params": "110M",
        "description": "Google Chinese BERT base model (via PyTorch + Transformers)",
    },
    "tfidf-char-ngram": {
        "name": "TF-IDF Character N-gram",
        "type": "TF-IDF",
        "layers": 1,
        "hidden_size": "dynamic (n_features)",
        "params": "N/A",
        "description": "Character-level TF-IDF weighted n-gram embedding (fallback)",
    },
}
class BERTSimilarityEvaluator:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.vectorizer = None
        self.fallback_mode = False
        self.hidden_size = 768
    def _check_model_cached(self, model_name: str) -> bool:
        import os as _os
        try:
            from huggingface_hub import try_to_load_from_cache
            config_file = try_to_load_from_cache(model_name, "config.json")
            if config_file and _os.path.exists(config_file):
                return True
        except Exception:
            pass
        cache_dir = _os.path.join(
            _os.path.expanduser("~"), ".cache", "huggingface", "hub",
            "models--" + model_name.replace("/", "--")
        )
        if _os.path.exists(cache_dir):
            snapshots = _os.path.join(cache_dir, "snapshots")
            if _os.path.exists(snapshots):
                for d in _os.listdir(snapshots):
                    snapshot_dir = _os.path.join(snapshots, d)
                    if _os.path.isdir(snapshot_dir):
                        if _os.path.exists(_os.path.join(snapshot_dir, "config.json")):
                            if _os.path.exists(_os.path.join(snapshot_dir, "pytorch_model.bin")) or \
                               _os.path.exists(_os.path.join(snapshot_dir, "model.safetensors")):
                                return True
        return False
    def _load_model(self, model_name: str = "bert-base-chinese"):
        if self.model is not None:
            return
        if self.fallback_mode:
            return
        if not self._check_model_cached(model_name):
            print(f"[BERT] Model {model_name} not found in local cache")
            print("[BERT] Unable to download (network unavailable)")
            print("[BERT] Activating TF-IDF character n-gram fallback mode ...")
            self._init_fallback()
            return
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[BERT] Loading {model_name} on {self.device} ...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, local_files_only=True
            )
            self.model = AutoModel.from_pretrained(
                model_name, local_files_only=True
            )
            self.model.to(self.device)
            self.model.eval()
            self.hidden_size = self.model.config.hidden_size
            print(f"[BERT] Model loaded successfully. Hidden size: {self.hidden_size}")
        except Exception as e:
            print(f"[BERT] Failed to load model: {e}")
            print("[BERT] Activating TF-IDF character n-gram fallback mode ...")
            self._init_fallback()
    def _init_fallback(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.fallback_mode = True
        self.vectorizer = None
        self.hidden_size = 768
        print("[FALLBACK] TF-IDF character n-gram mode active")
    def _fit_fallback(self, texts: List[str]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            max_features=768,
            sublinear_tf=True,
        )
        self.vectorizer.fit(texts)
        print(f"[FALLBACK] Fitted vectorizer with {len(self.vectorizer.get_feature_names_out())} features")
    def encode(self, texts: List[str], pooling: str = "mean", batch_size: int = 8) -> np.ndarray:
        if self.fallback_mode:
            return self._encode_fallback(texts, pooling)
        import torch
        self._load_model()
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            encoded = self.tokenizer(
                batch, padding=True, truncation=True,
                max_length=512, return_tensors="pt"
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            with torch.no_grad():
                outputs = self.model(**encoded)
            if pooling == "cls":
                embeddings = outputs.last_hidden_state[:, 0, :]
            elif pooling == "max":
                input_mask_expanded = encoded["attention_mask"].unsqueeze(-1).expand(
                    outputs.last_hidden_state.size()
                ).float()
                outputs.last_hidden_state[input_mask_expanded == 0] = -1e9
                embeddings = torch.max(outputs.last_hidden_state, 1)[0]
            else:
                input_mask_expanded = encoded["attention_mask"].unsqueeze(-1).expand(
                    outputs.last_hidden_state.size()
                ).float()
                embeddings = torch.sum(outputs.last_hidden_state * input_mask_expanded, 1) / torch.clamp(
                    input_mask_expanded.sum(1), min=1e-9
                )
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.append(embeddings.cpu().numpy())
        return np.vstack(all_embeddings)
    def _encode_fallback(self, texts: List[str], pooling: str = "mean") -> np.ndarray:
        if self.vectorizer is None:
            all_texts = []
            if hasattr(self, "_cached_train_texts"):
                all_texts = self._cached_train_texts
            all_texts = all_texts + texts
            self._fit_fallback(all_texts)
        embs = self.vectorizer.transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embs = embs / norms
        return embs
    def fit_vectorizer(self, corpus: List[str]):
        self._cached_train_texts = corpus
        if self.fallback_mode and self.vectorizer is None:
            self._fit_fallback(corpus)
    def similarity_matrix(self, ref_embs: np.ndarray, cand_embs: np.ndarray) -> np.ndarray:
        return np.dot(ref_embs, cand_embs.T)
    def pairwise_similarities(self, ref_embs: np.ndarray, cand_embs: np.ndarray) -> np.ndarray:
        return np.sum(ref_embs * cand_embs, axis=1)
    def bootstrap_confidence_interval(
        self, similarities: np.ndarray, n_bootstrap: int = 1000, alpha: float = 0.05
    ) -> Dict[str, float]:
        rng = np.random.RandomState(42)
        means = []
        n = len(similarities)
        for _ in range(n_bootstrap):
            sample = rng.choice(similarities, size=n, replace=True)
            means.append(np.mean(sample))
        lower = np.percentile(means, alpha / 2 * 100)
        upper = np.percentile(means, (1 - alpha / 2) * 100)
        return {
            "mean": float(np.mean(similarities)),
            "std": float(np.std(similarities)),
            "ci_lower": float(lower),
            "ci_upper": float(upper),
            "ci_level": 1 - alpha,
            "n_bootstrap": n_bootstrap,
        }
    def wilcoxon_test(self, group_a: np.ndarray, group_b: np.ndarray) -> Dict[str, Any]:
        statistic, p_value = stats.wilcoxon(group_a, group_b)
        return {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "significant": bool(p_value < 0.05),
            "alpha": 0.05,
        }
    def pearson_correlation(self, scores: np.ndarray, bleu_scores: np.ndarray) -> Dict[str, Any]:
        r, p_value = stats.pearsonr(scores, bleu_scores)
        return {
            "pearson_r": float(r),
            "p_value": float(p_value),
            "significant": bool(p_value < 0.05),
            "r_squared": float(r ** 2),
        }
    def spearman_correlation(self, scores: np.ndarray, bleu_scores: np.ndarray) -> Dict[str, Any]:
        rho, p_value = stats.spearmanr(scores, bleu_scores)
        return {
            "spearman_rho": float(rho),
            "p_value": float(p_value),
            "significant": bool(p_value < 0.05),
        }
    def t_test_onesample(self, similarities: np.ndarray, popmean: float = 0.5) -> Dict[str, Any]:
        statistic, p_value = stats.ttest_1samp(similarities, popmean)
        return {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "significant": bool(p_value < 0.05),
            "popmean": popmean,
            "mean": float(np.mean(similarities)),
        }
def segment_texts(text: str, min_len: int = 40) -> List[Dict[str, Any]]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    segments = []
    for para in paragraphs:
        segments.append({
            "text": para,
            "length": len(para),
            "type": "heading" if para.startswith("【") else "content",
        })
    return segments
def align_segments(ref_segs: List[Dict], cand_segs: List[Dict],
                   ref_emb: np.ndarray, cand_emb: np.ndarray,
                   threshold: float = 0.7) -> List[Dict]:
    aligned = []
    for i, rs in enumerate(ref_segs):
        sims = np.dot(cand_emb, ref_emb[i])
        best_j = int(np.argmax(sims))
        best_sim = float(sims[best_j])
        aligned.append({
            "ref_text": rs["text"],
            "ref_type": rs["type"],
            "best_cand_text": cand_segs[best_j]["text"] if best_j < len(cand_segs) else "",
            "best_cand_type": cand_segs[best_j]["type"] if best_j < len(cand_segs) else "",
            "similarity": best_sim,
            "match_quality": "high" if best_sim >= threshold else "medium" if best_sim >= 0.5 else "low",
        })
    return aligned
def run_test_iteration(
    evaluator: BERTSimilarityEvaluator,
    references: List[str],
    candidates: List[str],
    pooling: str = "mean",
    batch_size: int = 8,
) -> Dict[str, Any]:
    t0 = time.time()
    ref_embs = evaluator.encode(references, pooling=pooling, batch_size=batch_size)
    cand_embs = evaluator.encode(candidates, pooling=pooling, batch_size=batch_size)
    pairwise = evaluator.pairwise_similarities(ref_embs, cand_embs)
    ci = evaluator.bootstrap_confidence_interval(pairwise)
    matrix = evaluator.similarity_matrix(ref_embs, cand_embs)
    mean_sim = float(np.mean(pairwise))
    std_sim = float(np.std(pairwise))
    median_sim = float(np.median(pairwise))
    min_sim = float(np.min(pairwise))
    max_sim = float(np.max(pairwise))
    t_test = evaluator.t_test_onesample(pairwise, popmean=0.5)
    return {
        "pooling": pooling,
        "batch_size": batch_size,
        "pairwise_similarities": pairwise.tolist(),
        "mean_similarity": mean_sim,
        "std_similarity": std_sim,
        "median_similarity": median_sim,
        "min_similarity": min_sim,
        "max_similarity": max_sim,
        "confidence_interval": ci,
        "t_test": t_test,
        "similarity_matrix": matrix.tolist(),
        "embedding_dim": evaluator.hidden_size,
        "elapsed_seconds": float(time.time() - t0),
    }
def evaluate_with_bert(bleu_data_path: str = None) -> Dict[str, Any]:
    print("=" * 70)
    print("  BERT Semantic Similarity Evaluation System")
    print("  (with TF-IDF character n-gram fallback)")
    print("=" * 70)
    evaluator = BERTSimilarityEvaluator()
    print("\n[Model Check] Attempting to load bert-base-chinese ...")
    evaluator._load_model("bert-base-chinese")
    if evaluator.fallback_mode:
        print("[Model] Using TF-IDF character n-gram fallback")
        model_name = "tfidf-char-ngram"
    else:
        print("[Model] Using bert-base-chinese successfully")
        model_name = "bert-base-chinese"
    print("\nLoading case set references ...")
    with open(_CASE_SET_PATH, "r", encoding="utf-8") as f:
        case_set = json.load(f)
    ref_reports = []
    case_ids = []
    for item in case_set:
        for msg in item.get("messages", []):
            if msg.get("role") == "assistant":
                ref_reports.append(msg["content"])
                case_ids.append(item.get("id") or item.get("case_id", "unknown"))
                break
    print(f"  Loaded {len(ref_reports)} reference reports")
    from evaluation.enhanced_generator import generate_enhanced_report
    report_map = {
        "dialog_001": ("北京朝阳区", "较高风险", "VI", "城市区域风险评估"),
        "dialog_002": ("武汉蔡甸区", "较低风险", "III", "郊区区域风险评估"),
        "dialog_003": ("深圳南山区", "高风险", "V", "沿海城市风险评估"),
        "dialog_004": ("武汉武昌区", "中等风险", "IV", "高校区域风险评估"),
        "dialog_005": ("上海浦东新区", "极高风险", "VI", "机场净空区风险评估"),
        "dialog_006": ("杭州西湖区", "中等风险", "IV", "旅游景区风险评估"),
        "dialog_007": ("苏州工业园区", "较低风险", "III", "工业区域风险评估"),
        "dialog_008": ("广州天河区", "较高风险", "V", "政府机关区域风险评估"),
        "dialog_009": ("昆明市", "中等风险", "IV", "高原城市风险评估"),
        "dialog_010": ("成都锦江区", "较低风险", "III", "河流沿岸风险评估"),
    }
    candidates = []
    for item in case_set:
        cid = item.get("id") or item.get("case_id", "")
        if cid in report_map:
            region, risk_level, sail, scenario = report_map[cid]
            report = generate_enhanced_report(
                region=region, risk_level=risk_level,
                sail_level=sail, scenario=scenario, case_id=cid
            )
            candidates.append(report)
    print(f"  Generated {len(candidates)} candidate reports\n")
    if evaluator.fallback_mode:
        evaluator.fit_vectorizer(ref_reports + candidates)
    if evaluator.fallback_mode:
        iterations = []
        tfidf_configs = [
            {"name": "char_2-4", "ngram_range": (2, 4), "analyzer": "char_wb"},
            {"name": "char_1-3", "ngram_range": (1, 3), "analyzer": "char_wb"},
            {"name": "word_1-2", "ngram_range": (1, 2), "analyzer": "word"},
        ]
        print("Running evaluation iterations (TF-IDF multi-config) ...")
        for i, cfg in enumerate(tfidf_configs):
            print(f"  Iteration {i+1}/{len(tfidf_configs)}: config={cfg['name']} (ngram={cfg['ngram_range']}, analyzer={cfg['analyzer']}) ...")
            cfg_evaluator = BERTSimilarityEvaluator()
            cfg_evaluator.fallback_mode = True
            cfg_evaluator._init_fallback()
            cfg_evaluator.vectorizer = None
            from sklearn.feature_extraction.text import TfidfVectorizer
            cfg_evaluator.vectorizer = TfidfVectorizer(
                analyzer=cfg["analyzer"],
                ngram_range=cfg["ngram_range"],
                max_features=768,
                sublinear_tf=True,
            )
            cfg_evaluator.vectorizer.fit(ref_reports + candidates)
            cfg_evaluator.hidden_size = len(cfg_evaluator.vectorizer.get_feature_names_out())
            print(f"    Vectorizer fitted with {cfg_evaluator.hidden_size} features")
            result = run_test_iteration(
                cfg_evaluator, ref_reports, candidates,
                pooling="mean", batch_size=8,
            )
            result["iteration_id"] = i + 1
            result["model"] = model_name
            result["pooling"] = "mean"
            result["tfidf_config"] = cfg["name"]
            iterations.append(result)
            print(f"    Mean similarity: {result['mean_similarity']:.4f}, "
                  f"CI: [{result['confidence_interval']['ci_lower']:.4f}, "
                  f"{result['confidence_interval']['ci_upper']:.4f}]")
    else:
        pooling_strategies = ["mean", "cls", "max"]
        iterations = []
        print("Running evaluation iterations ...")
        for i, pooling in enumerate(pooling_strategies):
            print(f"  Iteration {i+1}/{len(pooling_strategies)}: pooling={pooling}, batch_size=8 ...")
            result = run_test_iteration(
                evaluator, ref_reports, candidates,
                pooling=pooling, batch_size=8,
            )
            result["iteration_id"] = i + 1
            result["model"] = model_name
            iterations.append(result)
            print(f"    Mean similarity: {result['mean_similarity']:.4f}, "
                  f"CI: [{result['confidence_interval']['ci_lower']:.4f}, "
                  f"{result['confidence_interval']['ci_upper']:.4f}]")
    ref_embs = evaluator.encode(ref_reports, pooling="mean")
    cand_embs = evaluator.encode(candidates, pooling="mean")
    segment_analysis = []
    for idx in range(len(ref_reports)):
        ref_segs = segment_texts(ref_reports[idx])
        cand_segs = segment_texts(candidates[idx])
        if ref_segs and cand_segs:
            rs_emb = evaluator.encode([s["text"] for s in ref_segs], pooling="mean")
            cs_emb = evaluator.encode([s["text"] for s in cand_segs], pooling="mean")
            aligned = align_segments(ref_segs, cand_segs, rs_emb, cs_emb)
            segment_analysis.append({
                "case_id": case_ids[idx],
                "ref_segments": len(ref_segs),
                "cand_segments": len(cand_segs),
                "alignments": aligned,
                "avg_segment_similarity": float(np.mean([a["similarity"] for a in aligned])),
            })
    pairwise_sims_all = [np.array(it["pairwise_similarities"]) for it in iterations]
    wilcoxon_tests = {}
    if len(pairwise_sims_all) >= 2:
        w1 = evaluator.wilcoxon_test(pairwise_sims_all[0], pairwise_sims_all[1])
        wilcoxon_tests = {"iter1_vs_iter2": w1}
        if len(pairwise_sims_all) >= 3:
            w2 = evaluator.wilcoxon_test(pairwise_sims_all[0], pairwise_sims_all[2])
            wilcoxon_tests["iter1_vs_iter3"] = w2
    bleu_case_scores = []
    if bleu_data_path and os.path.exists(bleu_data_path):
        with open(bleu_data_path, "r", encoding="utf-8") as f:
            bleu_data = json.load(f)
        per_case = (
            bleu_data.get("enhanced", bleu_data.get("baseline", {}))
            .get("per_case_results", [])
        )
        bleu_case_scores = [c["bleu"] for c in per_case][:len(pairwise_sims_all[0])]
    pearson_result = None
    spearman_result = None
    if len(bleu_case_scores) == len(pairwise_sims_all[0]):
        pearson_result = evaluator.pearson_correlation(
            pairwise_sims_all[0], np.array(bleu_case_scores)
        )
        spearman_result = evaluator.spearman_correlation(
            pairwise_sims_all[0], np.array(bleu_case_scores)
        )
    overall = {
        "evaluation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model_name,
        "model_type": MODEL_CONFIGS[model_name]["type"],
        "model_layers": MODEL_CONFIGS[model_name]["layers"],
        "hidden_size": evaluator.hidden_size,
        "num_cases": len(ref_reports),
        "num_iterations": len(iterations),
        "avg_similarity": float(np.mean([it["mean_similarity"] for it in iterations])),
        "std_similarity": float(np.mean([it["std_similarity"] for it in iterations])),
        "pooling_strategies": [it.get("pooling", "") for it in iterations],
        "tfidf_configs": [it.get("tfidf_config", "") for it in iterations],
        "device": "cpu",
        "framework": "sklearn TfidfVectorizer (fallback) | PyTorch + Transformers (BERT)",
        "fallback_used": evaluator.fallback_mode,
    }
    report = {
        "overall": overall,
        "iterations": iterations,
        "wilcoxon_tests": wilcoxon_tests,
        "pearson_correlation": pearson_result,
        "spearman_correlation": spearman_result,
        "segment_analysis": segment_analysis,
        "case_ids": case_ids,
        "bleu_scores_per_case": bleu_case_scores if bleu_case_scores else None,
    }
    report_path = os.path.join(_OUTPUT_DIR, "bert_similarity_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, ensure_ascii=False, indent=2, fp=f)
    print(f"\nResults saved to: {report_path}")
    return report