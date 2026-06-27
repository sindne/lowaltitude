// 使用高德 AMap 初始化并在地图上可视化后端返回的坐标与风险说明
const defaultCenter = [121.4737, 31.2304]; // [lng, lat]
let map = null;
let geocoder = null;
let infoWindow = null;
let overlays = [];
let assessmentHistory = [];
let currentAssessmentData = null;
let currentCity = null;
let kgNetwork = null;
let currentKnowledgeGraphData = null;

// 等待高德地图API加载完成后初始化
function initMap() {
    console.log('开始初始化地图');
    if (typeof AMap !== 'undefined') {
        try {
            map = new AMap.Map('map', {
                center: defaultCenter,
                zoom: 10,
            });
            
            console.log('地图初始化成功');
            
            // 只加载必要的插件
            AMap.plugin(['AMap.Geocoder', 'AMap.InfoWindow'], function() {
                try {
                    geocoder = new AMap.Geocoder();
                    infoWindow = new AMap.InfoWindow({
                        offset: new AMap.Pixel(0, -30),
                        autoMove: false
                    });
                    console.log('插件加载成功');
                } catch (e) {
                    console.error('插件初始化失败:', e);
                }
            });
        } catch (e) {
            console.error('地图初始化失败:', e);
            alert('地图初始化失败: ' + e.message);
        }
    } else {
        console.error('高德地图API未加载');
        alert('高德地图API未加载，请检查网络连接');
    }
}

window.onload = function() {
    console.log('页面加载完成');
    loadAssessmentHistory();
    initLegend();
    
    const chatSendBtn = document.getElementById('chatSend');
    const evaluateBtn = document.getElementById('evaluateBtn');
    const weatherBtn = document.getElementById('weatherBtn');
    const highRiskBtn = document.getElementById('highRiskBtn');
    const compareBtn = document.getElementById('compareBtn');
    const reportBtn = document.getElementById('reportBtn');
    
    console.log('检查按钮元素:', {
        chatSendBtn: chatSendBtn,
        evaluateBtn: evaluateBtn,
        weatherBtn: weatherBtn,
        highRiskBtn: highRiskBtn,
        compareBtn: compareBtn,
        reportBtn: reportBtn
    });
    
    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', function() {
            const region = document.getElementById('chatInput').value.trim();
            if (region) {
                document.getElementById('regionInput').value = region;
                submitRegion();
            }
        });
    }
    
    if (document.getElementById('chatInput')) {
        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const region = this.value.trim();
                if (region) {
                    document.getElementById('regionInput').value = region;
                    submitRegion();
                }
            }
        });
    }
    
    if (evaluateBtn) {
        evaluateBtn.addEventListener('click', submitRegion);
        console.log('评估按钮事件已绑定');
    }
    
    if (weatherBtn) {
        weatherBtn.addEventListener('click', quickWeatherCheck);
        console.log('天气查询按钮事件已绑定');
    }
    
    if (highRiskBtn) {
        highRiskBtn.addEventListener('click', analyzeHighRisk);
        console.log('高风险分析按钮事件已绑定');
    }
    
    if (compareBtn) {
        compareBtn.addEventListener('click', compareCities);
        console.log('城市对比按钮事件已绑定');
    }
    
    if (reportBtn) {
        reportBtn.addEventListener('click', generateReport);
        console.log('生成报告按钮事件已绑定');
    }
    
    // 知识图谱视图切换按钮
    const showTreeViewBtn = document.getElementById('showTreeView');
    const showNetworkViewBtn = document.getElementById('showNetworkView');
    
    if (showTreeViewBtn) {
        showTreeViewBtn.addEventListener('click', function() {
            showKnowledgeGraphView('tree');
        });
    }
    
    if (showNetworkViewBtn) {
        showNetworkViewBtn.addEventListener('click', function() {
            showKnowledgeGraphView('network');
        });
    }
    
    // 检查高德地图是否加载完成
    if (typeof AMap !== 'undefined' && AMap.plugin) {
        initMap();
    } else {
        // 延迟一下再尝试
        console.log('等待高德地图API加载...');
        setTimeout(function() {
            if (typeof AMap !== 'undefined') {
                initMap();
            } else {
                console.error('高德地图API加载超时');
            }
        }, 2000);
    }
};

// 行政区划边界数据缓存
let districtBoundaryCache = {};
function clearLayer() {
    if (overlays.length) {
        overlays.forEach(ov => ov.setMap && ov.setMap(null));
        overlays = [];
    }
}

function clearRoadmap() {
    const r = document.getElementById('roadmap');
    if (r) r.innerHTML = '';
}

function geocodeAddress(address) {
    return new Promise((resolve, reject) => {
        if (!geocoder) return reject('地理编码器不可用');
        try {
            geocoder.getLocation(address, function(status, result) {
                const geocodes = result && (result.geocodes || result.geocodes);
                if (geocodes && geocodes.length) {
                    const loc = geocodes[0].location;
                    if (Array.isArray(loc)) return resolve([loc[0], loc[1]]);
                    if (loc && typeof loc.lng !== 'undefined' && typeof loc.lat !== 'undefined') {
                        return resolve([loc.lng, loc.lat]);
                    }
                }
                if (result && result.location) {
                    const loc = result.location;
                    if (Array.isArray(loc)) return resolve([loc[0], loc[1]]);
                    if (loc && typeof loc.lng !== 'undefined' && typeof loc.lat !== 'undefined') {
                        return resolve([loc.lng, loc.lat]);
                    }
                }
                reject('未找到匹配地址');
            });
        } catch (e) {
            reject(e);
        }
    });
}

async function submitRegion() {
    const region = document.getElementById('regionInput').value.trim();
    if (!region) return alert('请输入区域描述');
    
    console.log('开始评估:', region);
    
    if (!map) {
        console.log('地图未初始化，等待地图加载...');
        alert('地图正在加载中，请稍候再试');
        return;
    }
    
    document.getElementById('riskResult').innerText = '评估中...';
    clearRoadmap();
    clearLayer();
    
    try {
        console.log('发送请求到后端...');
        const resp = await fetch('/evaluate', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({region})
        });
        
        console.log('收到后端响应');
        const data = await resp.json();
        console.log('解析数据:', data);
        
        const level = data.risk_level || '未知';
        const riskData = data.risk_data || {};
        const explanation = riskData.explanation || '';
        const coords = riskData.coordinates || [];
        const processSteps = riskData.process || [];
        const knowledgeGraph = riskData.knowledge_graph || null;

        let resultText = `风险等级: ${level}\n\n说明: ${explanation}`;
        
        if (knowledgeGraph) {
            resultText += `\n\n知识图谱:\n`;
            resultText += `   实体数量: ${knowledgeGraph.entities?.length || 0}\n`;
            resultText += `   关系数量: ${knowledgeGraph.relations?.length || 0}\n`;
            if (knowledgeGraph.risk_factors && knowledgeGraph.risk_factors.length > 0) {
                resultText += `   风险因素: ${knowledgeGraph.risk_factors.map(f => f.name).join(', ')}\n`;
            }
        }

        document.getElementById('riskResult').innerText = resultText;

        // 显示SORA评估结果
        const soraAssessment = riskData.sora_assessment;
        if (soraAssessment) {
            const soraPanel = document.getElementById('soraResultPanel');
            const soraContent = document.getElementById('soraResultContent');
            soraPanel.style.display = 'block';
            
            const soraData = soraAssessment.sora_assessment || {};
            const weightedData = soraAssessment.weighted_assessment || {};
            
            soraContent.innerHTML = `
                <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #3b82f6;">
                    <div style="font-size:11px;color:#64748b;">SAIL等级</div>
                    <div style="font-size:18px;font-weight:bold;color:#1e40af;">${soraData.sail_level || 'N/A'}</div>
                </div>
                <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #10b981;">
                    <div style="font-size:11px;color:#64748b;">地面风险等级</div>
                    <div style="font-size:18px;font-weight:bold;color:#065f46;">${soraData.ground_risk_level || 'N/A'}</div>
                </div>
                <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #f59e0b;">
                    <div style="font-size:11px;color:#64748b;">空中风险等级</div>
                    <div style="font-size:18px;font-weight:bold;color:#92400e;">${soraData.air_risk_class || 'N/A'}</div>
                </div>
                <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #8b5cf6;">
                    <div style="font-size:11px;color:#64748b;">综合评分</div>
                    <div style="font-size:18px;font-weight:bold;color:#5b21b6;">${soraAssessment.final_risk_score || 'N/A'}</div>
                </div>
                <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #ef4444;">
                    <div style="font-size:11px;color:#64748b;">风险等级</div>
                    <div style="font-size:18px;font-weight:bold;color:#dc2626;">${soraAssessment.risk_level || 'N/A'}</div>
                </div>
                <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #64748b;">
                    <div style="font-size:11px;color:#64748b;">加权验证分</div>
                    <div style="font-size:18px;font-weight:bold;color:#334155;">${weightedData.weighted_score || 'N/A'}</div>
                </div>
            `;
        }
        
        // 显示LLM评估结果
        const llmAssessment = riskData.llm_assessment;
        if (llmAssessment && llmAssessment.available) {
            const llmPanel = document.getElementById('llmResultPanel');
            const llmContent = document.getElementById('llmResultContent');
            llmPanel.style.display = 'block';
            
            llmContent.innerHTML = `
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
                    <div style="padding:8px;background:white;border-radius:6px;">
                        <div style="font-size:11px;color:#64748b;">LLM风险评分</div>
                        <div style="font-size:18px;font-weight:bold;color:#92400e;">${llmAssessment.llm_risk_score}</div>
                    </div>
                    <div style="padding:8px;background:white;border-radius:6px;">
                        <div style="font-size:11px;color:#64748b;">LLM风险等级</div>
                        <div style="font-size:18px;font-weight:bold;color:#dc2626;">${llmAssessment.llm_risk_level}</div>
                    </div>
                    <div style="padding:8px;background:white;border-radius:6px;">
                        <div style="font-size:11px;color:#64748b;">LLM校正</div>
                        <div style="font-size:18px;font-weight:bold;color:#059669;">${llmAssessment.llm_correction > 0 ? '+' : ''}${llmAssessment.llm_correction}</div>
                    </div>
                </div>
                <div style="padding:8px;background:white;border-radius:6px;font-size:12px;">
                    <div style="color:#64748b;">使用模型: ${llmAssessment.model_name} | 置信度: ${(llmAssessment.confidence * 100).toFixed(0)}%</div>
                </div>
            `;
        }

        currentCity = region;
        currentAssessmentData = data;
        saveAssessmentToHistory(region, data);
        
        let weatherData = {condition: '获取中', temperature: 'N/A'};
        try {
            const weatherResp = await fetch('/weather', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({city: region})
            });
            const weatherResult = await weatherResp.json();
            if (weatherResult.success) {
                weatherData = weatherResult.weather;
            }
        } catch (e) {
            console.error('获取天气数据失败:', e);
        }
        
        showRealTimeInfo(
            weatherData,
            {type: '城市'},
            {}
        );

        const color = level.includes('高') ? '#ff0000' : level.includes('中') ? '#ff8c00' : '#00a650';

        // 渲染评估过程路线图 - 树状紧凑结构
        if (Array.isArray(processSteps) && processSteps.length > 0) {
            const roadmapEl = document.getElementById('roadmap');
            
            if (roadmapEl) {
                roadmapEl.innerHTML = '';
                const container = document.createElement('div');
                container.className = 'roadmap-container';
                
                processSteps.forEach((s) => {
                    const card = document.createElement('div');
                    card.className = 'roadmap-card';
                    card.dataset.step = s.step;
                    
                    const header = document.createElement('div');
                    header.className = 'card-header';
                    header.innerHTML = `<span class="card-step-number">${s.step}</span><span>${s.action}</span>`;
                    
                    const body = document.createElement('div');
                    body.className = 'card-body';
                    body.style.display = 'none';
                    
                    if (s.detail) {
                        body.innerHTML += `<p style="margin:0;"><strong>详细说明：</strong>${s.detail}</p>`;
                    }
                    
                    // 添加评估因素权重（第8步显示）
                    if (s.step === 8 && riskData.factors) {
                        let factorsHtml = '<div style="margin-top:8px;"><strong style="display:block;margin-bottom:6px;">评估因素权重：</strong><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">';
                        riskData.factors.forEach(factor => {
                            factorsHtml += `<div style="background:#f9fafb;padding:5px;border-radius:4px;border:1px solid #e5e7eb;"><div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-weight:600;font-size:12px;">${factor.name}</span><span style="background:linear-gradient(90deg,#06b6d4,#7c3aed);color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:bold;">${factor.weight}%</span></div>${factor.description ? `<div style="font-size:10px;color:#6b7280;margin-top:3px;">${factor.description}</div>` : ''}</div>`;
                        });
                        factorsHtml += '</div></div>';
                        body.innerHTML += factorsHtml;
                    }
                    
                    const expandBtn = document.createElement('button');
                    expandBtn.className = 'expand-button';
                    expandBtn.textContent = '展开';
                    expandBtn.onclick = function() {
                        const isExpanded = body.style.display === 'block';
                        body.style.display = isExpanded ? 'none' : 'block';
                        expandBtn.textContent = isExpanded ? '展开' : '收起';
                        card.classList.toggle('expanded', !isExpanded);
                    };
                    
                    header.appendChild(expandBtn);
                    card.appendChild(header);
                    card.appendChild(body);
                    container.appendChild(card);
                });
                
                roadmapEl.appendChild(container);
            }
        }

        // 处理风险区
        const riskAreas = riskData.risk_areas || [];
        
        console.log('=== 风险评估数据调试 ===');
        console.log('后端返回的完整data:', data);
        console.log('riskData:', riskData);
        console.log('coords:', coords);
        console.log('riskAreas:', riskAreas);
        console.log('riskAreas.length:', riskAreas.length);
        console.log('地图对象map是否存在:', !!map);
        console.log('========================');
        
        // 首先绘制城市整体边界（如果有的话）
        if (coords && Array.isArray(coords) && coords.length > 0) {
            console.log('绘制城市整体边界，坐标点数:', coords.length);
            const cityBoundary = new AMap.Polygon({
                path: coords,
                strokeColor: '#1e88e5',
                strokeWeight: 3,
                strokeStyle: 'dashed',
                fillColor: 'rgba(30, 136, 229, 0.05)',
                zIndex: 1
            });
            cityBoundary.setMap(map);
            overlays.push(cityBoundary);
        }
        
        // 优先使用后端返回的风险区数据（更可靠）
        if (riskAreas.length > 0) {
            console.log('使用后端返回的风险区数据渲染，共', riskAreas.length, '个区域');
            riskAreas.forEach((area, index) => {
                if (typeof area === 'object' && area !== null) {
                    const level = area.level || '中等风险';
                    const areaName = area.name || '';
                    const areaCoords = area.coordinates || area;
                    
                    if (Array.isArray(areaCoords) && areaCoords.length > 0) {
                        const paths = areaCoords;
                        if (paths.length > 0) {
                            let areaColor;
                            switch(level) {
                                case '低风险':
                                    areaColor = '#00a650';
                                    break;
                                case '较低风险':
                                    areaColor = '#71c671';
                                    break;
                                case '中等风险':
                                    areaColor = '#ff8c00';
                                    break;
                                case '较高风险':
                                    areaColor = '#ff4500';
                                    break;
                                case '高风险':
                                    areaColor = '#ff0000';
                                    break;
                                default:
                                    areaColor = color;
                            }
                            
                            const factors = riskData.factors || [
                                {name: '人口密度', weight: 41.6, desc: '区域人口密集程度，影响事故后果严重程度'},
                                {name: '空中交通', weight: 26.2, desc: '航线密集度、飞行高度层使用情况'},
                                {name: '建筑物密度', weight: 16.1, desc: '建筑物分布密度和高度，影响碰撞风险'},
                                {name: '天气条件', weight: 9.8, desc: '包括降水、能见度、风速等气象条件'},
                                {name: '地理拓扑', weight: 6.3, desc: '地理拓扑因素，评估飞行航线与周边重要设施的空间邻近程度'}
                            ];
                            
                            let maxWeightFactor = null;
                            let maxWeight = -1;
                            factors.forEach(f => {
                                if (f.weight > maxWeight) {
                                    maxWeight = f.weight;
                                    maxWeightFactor = f.name;
                                }
                            });
                            
                            const dynamicKeyFactors = [...(area.key_factors || [])];
                            if (maxWeightFactor && !dynamicKeyFactors.includes(maxWeightFactor)) {
                                dynamicKeyFactors.unshift(maxWeightFactor);
                            }
                            
                            // 无边界数据：绘制圆形标记+文字标注
                            if (area.no_boundary) {
                                const centerLng = areaCoords[0][0];
                                const centerLat = areaCoords[0][1];
                                const circleMarker = new AMap.CircleMarker({
                                    center: [centerLng, centerLat],
                                    radius: 12,
                                    strokeColor: areaColor,
                                    strokeWeight: 2.5,
                                    strokeOpacity: 0.9,
                                    fillColor: hexToRgba(areaColor, 0.3),
                                    zIndex: 10,
                                    extData: {
                                        level: level, name: areaName,
                                        type: 'district', explanation: area.explanation || '',
                                        key_factors: dynamicKeyFactors, factors: factors,
                                        no_boundary: true
                                    }
                                });
                                const textLabel = new AMap.Text({
                                    text: areaName + '\n(无轮廓数据)',
                                    position: [centerLng, centerLat],
                                    offset: new AMap.Pixel(0, -25),
                                    style: {
                                        'background-color': areaColor,
                                        'color': '#fff',
                                        'font-size': '10px',
                                        'padding': '2px 6px',
                                        'border-radius': '3px',
                                        'white-space': 'nowrap',
                                        'text-align': 'center'
                                    },
                                    zIndex: 11
                                });
                                 circleMarker.on('mouseover', function(e) {
                                     e.target.setOptions({ strokeWeight: 4, strokeOpacity: 1, fillColor: hexToRgba(areaColor, 0.45) });
                                     const data = e.target.getExtData();
                                     let typeLabel = '<div style="margin-bottom:4px;"><span style="color:#6b7280;">类型:</span> <span style="background:#fef2f2; color:#991b1b; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">无轮廓数据</span></div>';
                                     infoWindow.setContent(
                                         `<div style="padding:10px 14px; font-size:13px; min-width:220px; color:#0f172a; background:#f8fafc;">
                                         <div style="font-size:16px; font-weight:bold; margin-bottom:6px;">${data.name}</div>
                                         ${typeLabel}
                                         <div style="margin-bottom:4px;"><span style="color:#475569;">风险等级:</span> <span style="color:${areaColor}; font-weight:bold; font-size:14px;">${data.level}</span></div>
                                         </div>`);
                                     infoWindow.open(map, e.lnglat || e.target.getCenter());
                                 });
                                 circleMarker.on('mouseout', function(e) {
                                     infoWindow.close();
                                     e.target.setOptions({ strokeWeight: 2.5, strokeOpacity: 0.9, fillColor: hexToRgba(areaColor, 0.3) });
                                 });
                                overlays.push(circleMarker);
                                overlays.push(textLabel);
                                console.log(`[地图渲染] 无边界区域(标记): ${areaName}`);
                                return;
                            }
                            
                            const polygon = new AMap.Polygon({
                                path: paths,
                                strokeColor: areaColor,
                                strokeWeight: area.type === 'district' ? 2.5 : 1.5,
                                strokeOpacity: 0.9,
                                strokeStyle: area.type === 'district' ? 'solid' : 'dashed',
                                fillColor: hexToRgba(areaColor, 0.20),
                                zIndex: 10,
                                extData: {
                                    level: level,
                                    name: areaName,
                                    type: area.type || 'district',
                                    explanation: area.explanation || '',
                                    key_factors: dynamicKeyFactors,
                                    factors: factors
                                }
                            });
                            
                            console.log(`[地图渲染] 正在渲染区域: ${areaName}, 风险等级: ${level}, 坐标点数: ${paths.length}`);
                            console.log(`[地图渲染] 关键因素: ${dynamicKeyFactors.join(', ')}`);
                            
                            polygon.on('mouseover', function(e) {
                                e.target.setOptions({
                                    strokeWeight: 4,
                                    strokeOpacity: 1,
                                    fillColor: hexToRgba(areaColor, 0.35)
                                });
                                
                                const data = e.target.getExtData();
                                let factorsHtml = '';
                                if (data.factors) {
                                    factorsHtml = '<div style="margin-top:8px; padding-top:8px; border-top:1px solid #e5e7eb;"><strong style="display:block; margin-bottom:6px;">评估因素:</strong><div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:11px;">';
                                    data.factors.forEach(f => {
                                        const isKeyFactor = data.key_factors && data.key_factors.includes(f.name);
                                    const bgColor = isKeyFactor ? '#fef3c7' : '#f9fafb';
                                    const borderColor = isKeyFactor ? '#f59e0b' : '#e5e7eb';
                                    const label = isKeyFactor ? ' [关键]' : '';
                                    factorsHtml += `<div style="background:${bgColor}; padding:3px 5px; border-radius:3px; border:1px solid ${borderColor};"><span style="font-weight:600;">${f.name}${label}</span> <span style="color:#6b7280;">${f.weight}%</span></div>`;
                                    });
                                    factorsHtml += '</div></div>';
                                }
                                let typeLabel = '';
                                if (data.type === 'circle') {
                                    typeLabel = '<div style="margin-bottom:4px;"><span style="color:#6b7280;">类型:</span> <span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">圆形区域</span></div>';
                                } else if (data.type === 'district') {
                                    typeLabel = '<div style="margin-bottom:4px;"><span style="color:#6b7280;">类型:</span> <span style="background:#dcfce7; color:#166534; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">行政区划</span></div>';
                                }
                                let explanationHtml = '';
                                if (data.explanation) {
                                    explanationHtml = `<div style="margin-bottom:6px; padding:6px 8px; background:#f3f4f6; border-radius:4px; font-size:12px; line-height:1.4;">${data.explanation}</div>`;
                                }
                                let keyFactorsHtml = '';
                                if (data.key_factors && data.key_factors.length > 0) {
                                    keyFactorsHtml = `<div style="margin-bottom:4px;"><span style="color:#6b7280;">关键因素:</span> <span style="color:#f59e0b; font-weight:600;">${data.key_factors.join('、')}</span></div>`;
                                }
                                const content = data.name ? 
                                `<div style="padding:10px 14px; font-size:13px; min-width:260px; color:#0f172a; background:#f8fafc;"><div style="font-size:18px; font-weight:bold; margin-bottom:8px; color:#0f172a;">${data.name}</div>${typeLabel}<div style="margin-bottom:4px;"><span style="color:#475569;">风险等级:</span> <span style="color:${areaColor}; font-weight:bold; font-size:15px;">${data.level}</span></div>${keyFactorsHtml}${explanationHtml}${factorsHtml}</div>` : 
                                `<div style="padding:10px 14px; color:#0f172a; background:#f8fafc;">风险等级: ${data.level}</div>`;
                                infoWindow.setContent(content);
                                infoWindow.open(map, e.lnglat);
                            });
                            
                            polygon.on('mouseout', function(e) {
                                infoWindow.close();
                                e.target.setOptions({
                                    strokeWeight: area.type === 'district' ? 2.5 : 1.5,
                                    strokeOpacity: 0.9,
                                    fillColor: hexToRgba(areaColor, 0.20)
                                });
                            });
                            
                            polygon.setMap(map);
                            overlays.push(polygon);
                            
                            if (areaName) {
                                let sumLng = 0, sumLat = 0;
                                paths.forEach(p => {
                                    sumLng += p[0];
                                    sumLat += p[1];
                                });
                                const centerLng = sumLng / paths.length;
                                const centerLat = sumLat / paths.length;
                                
                                const marker = new AMap.Marker({
                                    position: [centerLng, centerLat],
                                    content: `<div style="background: rgba(255,255,255,0.95); padding: 4px 8px; border-radius: 4px; border: 1px solid ${areaColor}; font-size: 12px; white-space: nowrap; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">${areaName}</div>`,
                                    offset: new AMap.Pixel(-30, -10)
                                });
                                marker.setMap(map);
                                overlays.push(marker);
                            }
                        }
                    }
                }
            });
            
            // 关键：让地图自动适应所有风险区的视图范围
            if (overlays.length > 0) {
                console.log('地图自动适应视图范围，包含', overlays.length, '个覆盖物');
                map.setFitView(overlays, false, [60, 60, 60, 60]);
            }
            
            // 评估完成后，直接使用后端返回的知识图谱数据
            console.log('评估完成，设置知识图谱数据...');
            if (knowledgeGraph) {
                currentKnowledgeGraphData = knowledgeGraph;
                console.log('知识图谱已设置，实体数:', knowledgeGraph.entities?.length || 0, '关系数:', knowledgeGraph.relations?.length || 0);
                // 重新渲染知识图谱
                renderKnowledgeGraphNetworkModern();
                console.log('知识图谱已渲染完成');
            } else {
                console.log('后端没有返回知识图谱数据，尝试加载...');
                try {
                    await loadKnowledgeGraph(region);
                    console.log('知识图谱已加载');
                } catch (kgError) {
                    console.error('加载知识图谱失败:', kgError);
                }
            }
        }
    } catch (e) {
        console.error('评估过程出错:', e);
        alert('评估过程出错: ' + (e.message || e.toString()));
        document.getElementById('riskResult').innerText = '评估失败，请重试。错误信息: ' + (e.message || e.toString());
    }
}

function saveAssessmentToHistory(region, data) {
    const timestamp = new Date().toLocaleString('zh-CN');
    try {
        // 保存地图显示必需的数据，但避免过大
        const minimalData = {
            risk_level: data.risk_level,
            knowledge_graph: data.knowledge_graph || null,  // 保存知识图谱数据
            risk_data: {
                explanation: data.risk_data?.explanation || '',
                factors: data.risk_data?.factors || [],
                // 保存地图必需的坐标数据
                coordinates: data.risk_data?.coordinates || [],
                risk_areas: data.risk_data?.risk_areas || [],
                process: data.risk_data?.process || []
            }
        };
        
        const historyItem = {
            id: Date.now(),
            region: region,
            timestamp: timestamp,
            data: minimalData
        };
        
        assessmentHistory.unshift(historyItem);
        if (assessmentHistory.length > 5) {
            assessmentHistory = assessmentHistory.slice(0, 5);
        }
        
        // 尝试保存，如果失败则移除坐标数据再保存
        try {
            localStorage.setItem('assessmentHistory', JSON.stringify(assessmentHistory));
        } catch (storageError) {
            console.warn('保存完整数据失败，尝试移除坐标数据:', storageError);
            // 如果仍然超限，移除坐标数据再保存
            const historyItemWithoutCoords = {
                ...historyItem,
                data: {
                    ...minimalData,
                    risk_data: {
                        ...minimalData.risk_data,
                        coordinates: [],
                        risk_areas: []
                    }
                }
            };
            assessmentHistory[0] = historyItemWithoutCoords;
            try {
                localStorage.setItem('assessmentHistory', JSON.stringify(assessmentHistory));
            } catch (secondError) {
                console.error('二次保存仍然失败:', secondError);
                assessmentHistory = assessmentHistory.slice(0, 3);
            }
        }
        
        renderAssessmentHistory();
    } catch (e) {
        console.error('保存历史记录失败:', e);
        // 如果localStorage失败，至少保留当前会话的记录
        assessmentHistory = assessmentHistory.slice(0, 3);
    }
}

function loadAssessmentHistory() {
    const saved = localStorage.getItem('assessmentHistory');
    if (saved) {
        try {
            assessmentHistory = JSON.parse(saved);
            renderAssessmentHistory();
        } catch (e) {
            console.error('加载历史记录失败:', e);
        }
    }
}

function deleteAssessmentFromHistory(id) {
    console.log('准备删除记录，ID:', id);
    
    if (!id) {
        console.log('无效的ID，取消删除');
        return;
    }
    
    const confirmed = window.confirm('确定要删除这条评估记录吗？');
    console.log('用户确认结果:', confirmed);
    
    if (confirmed && confirmed === true) {
        console.log('执行删除操作');
        const originalLength = assessmentHistory.length;
        assessmentHistory = assessmentHistory.filter(item => item.id !== id);
        
        if (assessmentHistory.length !== originalLength) {
            localStorage.setItem('assessmentHistory', JSON.stringify(assessmentHistory));
            renderAssessmentHistory();
            console.log('删除完成');
        } else {
            console.log('没有找到匹配的记录，取消删除');
        }
    } else {
        console.log('删除已取消');
    }
}

function renderAssessmentHistory() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    chatMessages.innerHTML = '';
    
    if (assessmentHistory.length === 0) {
        chatMessages.innerHTML = '<div style="padding:20px;text-align:center;color:#94a3b8;font-size:14px;">暂无评估记录</div>';
        return;
    }
    
    assessmentHistory.forEach((item, index) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'history-item';
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.innerHTML = '删除';
        deleteBtn.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            deleteAssessmentFromHistory(item.id);
        };
        
        const contentDiv = document.createElement('div');
        contentDiv.onclick = async function(e) {
            if (!e.target.closest('.delete-btn')) {
                await loadAssessmentFromHistory(item);
            }
        };
        const riskData = item.data.risk_data || {};
        const riskAreas = riskData.risk_areas || [];
        
        contentDiv.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <span style="font-weight:600;color:#1e293b;font-size:14px;">${item.region}</span>
                <span style="font-size:12px;color:#64748b;">${item.timestamp}</span>
            </div>
            <div style="font-size:12px;color:#64748b;">
                风险等级: ${item.data.risk_level || '未知'} | 
                区域数量: ${riskAreas.length || 0}
            </div>
        `;
        
        const tooltip = document.createElement('div');
        tooltip.style.cssText = 'position:absolute;left:100%;top:0;margin-left:10px;background:#ffffff;color:#1e293b;padding:12px 16px;border-radius:10px;font-size:12px;min-width:220px;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.1);display:none;border:1px solid #e2e8f0;';
        const highRiskCount = riskAreas.filter(a => a.level && a.level.includes('高')).length;
        const mediumRiskCount = riskAreas.filter(a => a.level && a.level.includes('中')).length;
        tooltip.innerHTML = `
            <div style="margin-bottom:10px;font-weight:700;font-size:13px;">${item.region} - 评估概览</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div style="background:#fef2f2;color:#dc2626;padding:6px 10px;border-radius:6px;border:1px solid #fecaca;">高风险: ${highRiskCount}</div>
                <div style="background:#fff7ed;color:#ea580c;padding:6px 10px;border-radius:6px;border:1px solid #fed7aa;">中等风险: ${mediumRiskCount}</div>
                <div style="background:#eff6ff;color:#2563eb;padding:6px 10px;border-radius:6px;border:1px solid #bfdbfe;">总区域: ${riskAreas.length}</div>
                <div style="background:#f0fdf4;color:#16a34a;padding:6px 10px;border-radius:6px;border:1px solid #bbf7d0;">等级: ${item.data.risk_level || '未知'}</div>
            </div>
        `;
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(deleteBtn);
        messageDiv.appendChild(tooltip);
        
        chatMessages.appendChild(messageDiv);
    });
}

async function loadAssessmentFromHistory(item) {
    console.log('加载历史记录:', item.region);
    console.log('历史记录数据:', item.data);
    currentAssessmentData = item.data;
    currentCity = item.region;
    
    document.getElementById('regionInput').value = item.region;
    const riskData = item.data.risk_data || {};
    document.getElementById('riskResult').innerText = `风险等级: ${item.data.risk_level || '未知'}\n\n说明: ${riskData.explanation || ''}`;
    
    let riskAreas = riskData.risk_areas || [];
    let coords = riskData.coordinates || [];
    const factors = riskData.factors || [];
    let processSteps = riskData.process || [];
    
    // 检查是否有坐标数据，如果没有尝试重新从后端获取
    if ((!coords || coords.length === 0) && (!riskAreas || riskAreas.length === 0)) {
        console.log('历史记录中没有坐标数据，尝试重新从后端获取...');
        try {
            const resp = await fetch('/evaluate', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({region: item.region})
            });
            const newData = await resp.json();
            console.log('重新获取的数据:', newData);
            
            // 更新数据
            currentAssessmentData = newData;
            const newRiskData = newData.risk_data || {};
            coords = newRiskData.coordinates || [];
            riskAreas = newRiskData.risk_areas || [];
            processSteps = newRiskData.process || [];
            
            // 更新保存的历史记录
            item.data = newData;
            saveAssessmentToHistory(item.region, newData);
            
        } catch (e) {
            console.error('重新获取数据失败:', e);
        }
    }
    
    // 检查是否有知识图谱数据，有就显示，没有就重新获取
    const kgData = currentAssessmentData.knowledge_graph || item.data.knowledge_graph;
    if (kgData && kgData.entities && kgData.entities.length > 0) {
        console.log('使用保存的知识图谱数据');
        currentKnowledgeGraphData = kgData;
        renderKnowledgeGraphNetworkModern();
    } else {
        console.log('没有保存的知识图谱数据，重新获取');
        try {
            const kgResp = await fetch('/knowledge_graph/visualize', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({region: item.region})
            });
            const kgResult = await kgResp.json();
            if (kgResult.success && kgResult.data) {
                currentKnowledgeGraphData = kgResult.data;
                renderKnowledgeGraphNetworkModern();
            }
        } catch (e) {
            console.error('获取知识图谱失败:', e);
        }
    }
    
    console.log('使用的coords:', coords);
    console.log('使用的riskAreas:', riskAreas);
    
    showRealTimeInfo(
        {condition: '已评估', temperature: 'N/A'},
        {type: '已评估城市'},
        {}
    );
    
    clearRoadmap();
    clearLayer();
    
    const color = (item.data.risk_level || '').includes('高') ? '#ff0000' : (item.data.risk_level || '').includes('中') ? '#ff8c00' : '#00a650';
    
    if (Array.isArray(processSteps) && processSteps.length > 0) {
        const roadmapEl = document.getElementById('roadmap');
        if (roadmapEl) {
            roadmapEl.innerHTML = '';
            const container = document.createElement('div');
            container.className = 'roadmap-container';
            
            processSteps.forEach((s) => {
                const card = document.createElement('div');
                card.className = 'roadmap-card';
                card.dataset.step = s.step;
                
                const header = document.createElement('div');
                header.className = 'card-header';
                header.innerHTML = `<span class="card-step-number">${s.step}</span><span>${s.action}</span>`;
                
                const body = document.createElement('div');
                body.className = 'card-body';
                body.style.display = 'none';
                
                if (s.detail) {
                    body.innerHTML += `<p style="margin:0;"><strong>详细说明：</strong>${s.detail}</p>`;
                }
                
                if (s.step === 8 && riskData.factors) {
                    let factorsHtml = '<div style="margin-top:8px;"><strong style="display:block;margin-bottom:6px;">评估因素权重：</strong><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">';
                    riskData.factors.forEach(factor => {
                        factorsHtml += `<div style="background:#f9fafb;padding:5px;border-radius:4px;border:1px solid #e5e7eb;"><div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-weight:600;font-size:12px;">${factor.name}</span><span style="background:linear-gradient(90deg,#06b6d4,#7c3aed);color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:bold;">${factor.weight}%</span></div>${factor.description ? `<div style="font-size:10px;color:#6b7280;margin-top:3px;">${factor.description}</div>` : ''}</div>`;
                    });
                    factorsHtml += '</div></div>';
                    body.innerHTML += factorsHtml;
                }
                
                const expandBtn = document.createElement('button');
                expandBtn.className = 'expand-button';
                expandBtn.textContent = '展开';
                expandBtn.onclick = function() {
                    const isExpanded = body.style.display === 'block';
                    body.style.display = isExpanded ? 'none' : 'block';
                    expandBtn.textContent = isExpanded ? '展开' : '收起';
                    card.classList.toggle('expanded', !isExpanded);
                };
                
                header.appendChild(expandBtn);
                card.appendChild(header);
                card.appendChild(body);
                container.appendChild(card);
            });
            
            roadmapEl.appendChild(container);
        }
    }
    
    if (coords && Array.isArray(coords) && coords.length > 0) {
        const cityBoundary = new AMap.Polygon({
            path: coords,
            strokeColor: '#1e88e5',
            strokeWeight: 3,
            strokeStyle: 'dashed',
            fillColor: 'rgba(30, 136, 229, 0.05)',
            zIndex: 1
        });
        cityBoundary.setMap(map);
        overlays.push(cityBoundary);
    }
    
    if (riskAreas.length > 0) {
        riskAreas.forEach((area, index) => {
            if (typeof area === 'object' && area !== null) {
                const level = area.level || '中等风险';
                const areaName = area.name || '';
                const areaCoords = area.coordinates || area;
                
                if (Array.isArray(areaCoords) && areaCoords.length > 0) {
                    const paths = areaCoords;
                    if (paths.length > 0) {
                        let areaColor;
                        switch(level) {
                            case '低风险':
                                areaColor = '#00a650';
                                break;
                            case '较低风险':
                                areaColor = '#71c671';
                                break;
                            case '中等风险':
                                areaColor = '#ff8c00';
                                break;
                            case '较高风险':
                                areaColor = '#ff4500';
                                break;
                            case '高风险':
                                areaColor = '#ff0000';
                                break;
                            default:
                                areaColor = color;
                        }
                        
                    // 动态找出权重最大的因素作为关键因素
                    const factors = riskData.factors || [
                        {name: '人口密度', weight: 41.6, desc: '区域人口密集程度，影响事故后果严重程度'},
                        {name: '空中交通', weight: 26.2, desc: '航线密集度、飞行高度层使用情况'},
                        {name: '建筑物密度', weight: 16.1, desc: '建筑物分布密度和高度，影响碰撞风险'},
                        {name: '天气条件', weight: 9.8, desc: '包括降水、能见度、风速等气象条件'},
                        {name: '地理拓扑', weight: 6.3, desc: '地理拓扑因素，评估飞行航线与周边重要设施的空间邻近程度'}
                    ];
                    
                    // 找出权重最大的因素
                    let maxWeightFactor = null;
                    let maxWeight = -1;
                    factors.forEach(f => {
                        if (f.weight > maxWeight) {
                            maxWeight = f.weight;
                            maxWeightFactor = f.name;
                        }
                    });
                    
                    // 将权重最大的因素添加到key_factors中
                    const dynamicKeyFactors = [...(area.key_factors || [])];
                    if (maxWeightFactor && !dynamicKeyFactors.includes(maxWeightFactor)) {
                        dynamicKeyFactors.unshift(maxWeightFactor);
                    }
                    
                    const polygon = new AMap.Polygon({
                        path: paths,
                        strokeColor: areaColor,
                        strokeWeight: 2,
                        fillColor: hexToRgba(areaColor, 0.25),
                        zIndex: 10,
                        extData: {
                            level: level,
                            name: areaName,
                            type: area.type || 'district',
                            explanation: area.explanation || '',
                            key_factors: dynamicKeyFactors,
                            factors: factors
                        }
                    });
                        
                        polygon.on('mouseover', function(e) {
                            const data = e.target.getExtData();
                            let factorsHtml = '';
                            if (data.factors) {
                                factorsHtml = '<div style="margin-top:8px; padding-top:8px; border-top:1px solid #e5e7eb;"><strong style="display:block; margin-bottom:6px;">评估因素:</strong><div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:11px;">';
                                data.factors.forEach(f => {
                                    const isKeyFactor = data.key_factors && data.key_factors.includes(f.name);
                                    const bgColor = isKeyFactor ? '#fef3c7' : '#f9fafb';
                                    const borderColor = isKeyFactor ? '#f59e0b' : '#e5e7eb';
                                    const label = isKeyFactor ? ' [关键]' : '';
                                    factorsHtml += `<div style="background:${bgColor}; padding:3px 5px; border-radius:3px; border:1px solid ${borderColor};"><span style="font-weight:600;">${f.name}${label}</span> <span style="color:#6b7280;">${f.weight}%</span></div>`;
                                });
                                factorsHtml += '</div></div>';
                            }
                            let typeLabel = '';
                            if (data.type === 'circle') {
                                typeLabel = '<div style="margin-bottom:4px;"><span style="color:#6b7280;">类型:</span> <span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">圆形区域</span></div>';
                            } else if (data.type === 'district') {
                                typeLabel = '<div style="margin-bottom:4px;"><span style="color:#6b7280;">类型:</span> <span style="background:#dcfce7; color:#166534; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">行政区划</span></div>';
                            }
                            let explanationHtml = '';
                            if (data.explanation) {
                                explanationHtml = `<div style="margin-bottom:6px; padding:6px 8px; background:#f3f4f6; border-radius:4px; font-size:12px; line-height:1.4;">${data.explanation}</div>`;
                            }
                            let keyFactorsHtml = '';
                            if (data.key_factors && data.key_factors.length > 0) {
                                keyFactorsHtml = `<div style="margin-bottom:4px;"><span style="color:#6b7280;">关键因素:</span> <span style="color:#f59e0b; font-weight:600;">${data.key_factors.join('、')}</span></div>`;
                            }
                            const content = data.name ? 
                                `<div style="padding:10px 14px; color:#0f172a; background:#f8fafc;"><div style="font-size:18px; font-weight:bold; margin-bottom:8px; color:#0f172a;">${data.name}</div>${typeLabel}<div style="margin-bottom:4px;"><span style="color:#475569;">风险等级:</span> <span style="color:${areaColor}; font-weight:bold; font-size:15px;">${data.level}</span></div>${keyFactorsHtml}${explanationHtml}${factorsHtml}</div>` : 
                                `<div style="padding:10px 14px; color:#0f172a; background:#f8fafc;">风险等级: ${data.level}</div>`;
                            infoWindow.setContent(content);
                            infoWindow.open(map, e.lnglat);
                        });
                        
                        polygon.on('mouseout', function() {
                            infoWindow.close();
                        });
                        
                        polygon.setMap(map);
                        overlays.push(polygon);
                        
                        if (areaName) {
                            let sumLng = 0, sumLat = 0;
                            paths.forEach(p => {
                                sumLng += p[0];
                                sumLat += p[1];
                            });
                            const centerLng = sumLng / paths.length;
                            const centerLat = sumLat / paths.length;
                            
                            const marker = new AMap.Marker({
                                position: [centerLng, centerLat],
                                content: `<div style="background: rgba(255,255,255,0.95); padding: 4px 8px; border-radius: 4px; border: 1px solid ${areaColor}; font-size: 12px; white-space: nowrap; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">${areaName}</div>`,
                                offset: new AMap.Pixel(-30, -10)
                            });
                            marker.setMap(map);
                            overlays.push(marker);
                        }
                    }
                }
            }
        });
        
        if (overlays.length > 0) {
            console.log('地图自动适应视图范围，包含', overlays.length, '个覆盖物');
            map.setFitView(overlays, false, [60, 60, 60, 60]);
        }
    }
}

function hexToRgba(hex, alpha) {
    const h = hex.replace('#','');
    const bigint = parseInt(h, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r},${g},${b},${alpha})`;
}

function initLegend() {
    const legend = document.getElementById('legend');
    if (legend) {
        legend.innerHTML = `
            <div style="font-weight:700;margin-bottom:6px;">风险等级</div>
            <div><span class="sw" style="background:#00a650;"></span> 低风险</div>
            <div><span class="sw" style="background:#71c671;"></span> 较低风险</div>
            <div><span class="sw" style="background:#ff8c00;"></span> 中等风险</div>
            <div><span class="sw" style="background:#ff4500;"></span> 较高风险</div>
            <div><span class="sw" style="background:#ff0000;"></span> 高风险</div>
        `;
    }
}

function showRealTimeInfo(weatherData, cityInfo, trafficData) {
    const infoContainer = document.getElementById('realTimeInfo');
    infoContainer.style.display = 'grid';
    
    const weatherCondition = weatherData && weatherData.condition || '未知';
    const weatherTemperature = weatherData && weatherData.temperature || 'N/A';
    const cityType = cityInfo && cityInfo.type || '城市';
    
    infoContainer.innerHTML = `
        <div class="info-card">
            <div class="info-card-label">天气状况</div>
            <div class="info-card-value">${weatherCondition}</div>
        </div>
        <div class="info-card">
            <div class="info-card-label">温度</div>
            <div class="info-card-value">${weatherTemperature}</div>
        </div>
        <div class="info-card">
            <div class="info-card-label">城市类型</div>
            <div class="info-card-value">${cityType}</div>
        </div>
        <div class="info-card">
            <div class="info-card-label">数据来源</div>
            <div class="info-card-value" style="font-size:14px;">本地LoRA微调模型 + 高德地图API</div>
        </div>
    `;
}

async function quickWeatherCheck() {
    console.log('天气查询按钮被点击');
    const city = currentCity || document.getElementById('regionInput').value.trim();
    if (!city) {
        alert('请先输入或选择一个城市');
        return;
    }
    
    document.getElementById('riskResult').innerText = '正在获取天气数据...';
    
    try {
        console.log('发送天气请求到:', city);
        const resp = await fetch('/weather', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({city})
        });
        console.log('收到响应，状态码:', resp.status);
        const data = await resp.json();
        console.log('解析的天气数据:', data);
        
        if (data.success) {
            const weather = data.weather;
            document.getElementById('riskResult').innerText = 
                `${city}天气信息\n\n` +
                `天气状况: ${weather.condition}\n` +
                `温度: ${weather.temperature}\n` +
                `风力: ${weather.wind_speed}\n` +
                `湿度: ${weather.humidity}\n` +
                `数据来源: ${weather.source}`;
        } else {
            document.getElementById('riskResult').innerText = '获取天气数据失败: 服务器返回错误';
        }
    } catch (e) {
        console.error('天气查询出错:', e);
        document.getElementById('riskResult').innerText = '获取天气数据失败: ' + (e.message || e.toString());
    }
}

function analyzeHighRisk() {
    console.log('高风险分析按钮被点击');
    if (!currentAssessmentData) {
        alert('请先进行一次风险评估');
        return;
    }
    
    const riskData = currentAssessmentData.risk_data || {};
    const riskAreas = riskData.risk_areas || [];
    const highRiskAreas = riskAreas.filter(a => a.level && a.level.includes('高'));
    
    if (highRiskAreas.length === 0) {
        document.getElementById('riskResult').innerText = '未发现高风险区域';
        return;
    }
    
    let analysis = '高风险区域分析报告\n\n';
    highRiskAreas.forEach((area, index) => {
        analysis += `${index + 1}. ${area.name}\n`;
        analysis += `   风险等级: ${area.level}\n`;
        analysis += `   关键因素: ${(area.key_factors || []).join('、')}\n`;
        analysis += `   说明: ${area.explanation || '无详细说明'}\n\n`;
    });
    
    analysis += `\n建议: 避免在上述区域进行低空飞行活动。`;
    document.getElementById('riskResult').innerText = analysis;
}

function compareCities() {
    console.log('城市对比按钮被点击');
    if (assessmentHistory.length < 2) {
        alert('需要至少2条评估记录才能进行对比');
        return;
    }
    
    let comparison = '城市风险对比报告\n\n';
    
    assessmentHistory.slice(0, 5).forEach((item, index) => {
        const riskData = item.data.risk_data || {};
        const riskAreas = riskData.risk_areas || [];
        const highRisk = riskAreas.filter(a => a.level && a.level.includes('高')).length;
        const totalAreas = riskAreas.length;
        
        comparison += `${index + 1}. ${item.region}\n`;
        comparison += `   评估时间: ${item.timestamp}\n`;
        comparison += `   整体风险: ${item.data.risk_level || '未知'}\n`;
        comparison += `   高风险区域: ${highRisk}/${totalAreas}\n\n`;
    });
    
    document.getElementById('riskResult').innerText = comparison;
}

function generateReport() {
    console.log('生成报告按钮被点击');
    if (!currentAssessmentData || !currentCity) {
        alert('请先进行一次风险评估');
        return;
    }
    
    const riskData = currentAssessmentData.risk_data || {};
    const riskAreas = riskData.risk_areas || [];
    const factors = riskData.factors || [];
    
    let report = `${currentCity} 低空空域风险评估报告\n`;
    report += `生成时间: ${new Date().toLocaleString('zh-CN')}\n`;
    report += '='.repeat(50) + '\n\n';
    
    report += '一、整体评估\n';
    report += `整体风险等级: ${currentAssessmentData.risk_level || '未知'}\n`;
    report += `评估区域数量: ${riskAreas.length}\n\n`;
    
    report += '二、评估因素权重\n';
    factors.forEach(f => {
        report += `  ${f.name}: ${f.weight}%\n`;
        if (f.description) report += `    ${f.description}\n`;
    });
    report += '\n';
    
    report += '三、风险区域分布\n';
    const riskCounts = {};
    riskAreas.forEach(a => {
        const level = a.level || '未知';
        riskCounts[level] = (riskCounts[level] || 0) + 1;
    });
    
    Object.entries(riskCounts).forEach(([level, count]) => {
        report += `  ${level}: ${count}个区域\n`;
    });
    
    report += '\n四、高风险区域详情\n';
    const highRiskAreas = riskAreas.filter(a => a.level && a.level.includes('高'));
    if (highRiskAreas.length === 0) {
        report += '  无高风险区域\n';
    } else {
        highRiskAreas.forEach(area => {
            report += `  - ${area.name}: ${area.explanation || '无说明'}\n`;
        });
    }
    
    report += '\n' + '='.repeat(50) + '\n';
    report += '报告生成: 低空空域环境风险评估系统';
    
    document.getElementById('riskResult').innerText = report;
}

// 新功能的JavaScript代码
window.addEventListener('load', function() {
    initTabs();
    initEnhancedFeatures();
});

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
            
            if (tabId === 'kg') {
                loadKnowledgeGraph();
            } else if (tabId === 'training') {
                loadIterationStatus();
            }
        });
    });
}

function initEnhancedFeatures() {
    const startIterationBtn = document.getElementById('startIteration');
    const stopIterationBtn = document.getElementById('stopIteration');
    const generateRouteBtn = document.getElementById('generateRouteBtn');
    const loadHistoryBtn = document.getElementById('loadHistoryBtn');
    
    if (startIterationBtn) {
        startIterationBtn.addEventListener('click', startIteration);
    }
    
    if (stopIterationBtn) {
        stopIterationBtn.addEventListener('click', stopIteration);
    }
    
    if (generateRouteBtn) {
        generateRouteBtn.addEventListener('click', generateDynamicRoute);
    }
    
    if (loadHistoryBtn) {
        loadHistoryBtn.addEventListener('click', loadAssessmentHistoryNew);
    }
    
    loadModelList();
}

let selectedModelName = null;

async function loadModelList() {
    const container = document.getElementById('modelList');
    if (!container) return;
    
    container.innerHTML = '<p>加载中...</p>';
    
    try {
        const resp = await fetch('/train/lora', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({action: 'list_models'})
        });
        
        const data = await resp.json();
        
        if (data.success && data.models) {
            renderModelList(data.models, container);
        } else {
            container.innerHTML = '<p>加载模型列表失败</p>';
        }
    } catch (e) {
        container.innerHTML = '<p>加载模型列表失败: ' + e.message + '</p>';
    }
}

function renderModelList(models, container) {
    if (models.length === 0) {
        container.innerHTML = '<p>暂无训练模型</p>';
        return;
    }
    
    let html = '<div style="display:flex;flex-wrap:wrap;gap:10px;">';
    
    models.forEach((model, index) => {
        const isSelected = selectedModelName === model.name;
        html += `
            <div style="
                padding: 12px 16px;
                background: ${isSelected ? '#dbeafe' : 'white'};
                border: 2px solid ${isSelected ? '#3b82f6' : '#e5e7eb'};
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s;
            " onclick="selectModel('${model.name}')">
                <div style="font-weight: 600; font-size: 14px;">${model.name}</div>
                <div style="font-size: 12px; color: #6b7280;">${model.created_at}</div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

async function selectModel(modelName) {
    selectedModelName = modelName;
    
    // 重新渲染模型列表以显示选中状态
    loadModelList();
    
    // 加载训练数据预览
    loadTrainingDataPreview(modelName);
    
    // 加载模型详细信息
    loadModelDetails(modelName);
}

async function loadTrainingDataPreview(modelName) {
    const container = document.getElementById('trainingDataPreview');
    if (!container) return;
    
    container.innerHTML = '<p>加载中...</p>';
    
    try {
        const resp = await fetch('/train/lora', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({action: 'get_training_data_preview', model_name: modelName})
        });
        
        const data = await resp.json();
        
        if (data.success && data.preview) {
            renderTrainingDataPreview(data.preview, container);
        } else {
            container.innerHTML = '<p>加载训练数据预览失败: ' + (data.error || '未知错误') + '</p>';
        }
    } catch (e) {
        container.innerHTML = '<p>加载训练数据预览失败: ' + e.message + '</p>';
    }
}

function renderTrainingDataPreview(preview, container) {
    let html = `
        <div style="margin-bottom: 15px; padding: 10px; background: #f0fdf4; border-radius: 6px;">
            <strong>总训练样本数:</strong> ${preview.total_samples}
        </div>
        <h4 style="margin-bottom: 10px;">训练数据预览（前5条）:</h4>
    `;
    
    preview.preview_samples.forEach((sample, index) => {
        html += `
            <div style="margin-bottom: 12px; padding: 12px; background: white; border-radius: 6px; border-left: 3px solid #3b82f6;">
                <div style="font-weight: 600; margin-bottom: 8px;">
                    样本 ${sample.index}: ${sample.type}
                </div>
                <div style="font-size: 13px; line-height: 1.6;">
                    ${renderSampleContent(sample.preview)}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function renderSampleContent(preview) {
    if (preview.user_query) {
        return `
            <div><strong>用户提问:</strong> ${preview.user_query}...</div>
            <div><strong>助手回复:</strong> ${preview.assistant_response}...</div>
        `;
    } else if (preview.region) {
        return `
            <div><strong>区域:</strong> ${preview.region}</div>
            <div><strong>风险等级:</strong> ${preview.risk_level}</div>
            <div><strong>因素数量:</strong> ${preview.factors_count}</div>
            <div><strong>说明:</strong> ${preview.explanation}...</div>
        `;
    } else {
        return `<div>${preview.content}...</div>`;
    }
}

async function loadModelDetails(modelName) {
    const container = document.getElementById('modelMetrics');
    if (!container) return;
    
    container.innerHTML = '<p>加载中...</p>';
    
    try {
        const resp = await fetch('/train/lora', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({action: 'get_model_details', model_name: modelName})
        });
        
        const data = await resp.json();
        
        if (data.success && data.details) {
            renderModelDetails(data.details, container);
        } else {
            container.innerHTML = '<p>加载模型详情失败: ' + (data.error || '未知错误') + '</p>';
        }
    } catch (e) {
        container.innerHTML = '<p>加载模型详情失败: ' + e.message + '</p>';
    }
}

function renderModelDetails(details, container) {
    let html = '';
    
    // 训练配置
    html += `
        <div style="margin-bottom: 20px;">
            <h4 style="margin-bottom: 10px;">训练配置:</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="padding: 10px; background: #f8fafc; border-radius: 6px;">
                    <strong>LoRA Rank:</strong> ${details.training_config?.lora_rank || '-'}
                </div>
                <div style="padding: 10px; background: #f8fafc; border-radius: 6px;">
                    <strong>LoRA Alpha:</strong> ${details.training_config?.lora_alpha || '-'}
                </div>
                <div style="padding: 10px; background: #f8fafc; border-radius: 6px;">
                    <strong>学习率:</strong> ${details.training_config?.learning_rate || '-'}
                </div>
                <div style="padding: 10px; background: #f8fafc; border-radius: 6px;">
                    <strong>Batch Size:</strong> ${details.training_config?.batch_size || '-'}
                </div>
                <div style="padding: 10px; background: #f8fafc; border-radius: 6px;">
                    <strong>训练轮数:</strong> ${details.training_config?.num_epochs || '-'}
                </div>
                <div style="padding: 10px; background: #f8fafc; border-radius: 6px;">
                    <strong>训练样本数:</strong> ${details.num_training_samples || '-'}
                </div>
            </div>
        </div>
    `;
    
    // 训练指标
    html += `
        <div style="margin-bottom: 20px;">
            <h4 style="margin-bottom: 10px;">训练指标:</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="padding: 10px; background: #fef3c7; border-radius: 6px;">
                    <strong>训练损失:</strong> ${details.metrics?.train_loss || '-'}
                </div>
                <div style="padding: 10px; background: #dbeafe; border-radius: 6px;">
                    <strong>困惑度:</strong> ${details.metrics?.perplexity || '-'}
                </div>
            </div>
        </div>
    `;
    
    // 准确率评估指标
    if (details.accuracy) {
        const accuracy = details.accuracy;
        const levelAccuracyPercent = (accuracy.level_accuracy * 100).toFixed(1);
        const levelCloseRatePercent = (accuracy.level_close_rate * 100).toFixed(1);
        const factorOverlapPercent = (accuracy.average_factor_overlap * 100).toFixed(1);
        const overallScorePercent = (accuracy.average_accuracy_score * 100).toFixed(1);
        
        html += `
            <div style="margin-bottom: 20px;">
                <h4 style="margin-bottom: 10px;">准确率评估:</h4>
                <div style="padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 16px; font-weight: bold; margin-bottom: 5px;">综合准确率分数</div>
                    <div style="font-size: 28px; font-weight: bold;">${overallScorePercent}%</div>
                    <div style="font-size: 12px; opacity: 0.9;">测试用例数: ${accuracy.total_tests}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div style="padding: 10px; background: #dcfce7; border-radius: 6px;">
                        <strong>风险等级准确率:</strong>
                        <div style="font-size: 18px; font-weight: bold; color: #16a34a;">${levelAccuracyPercent}%</div>
                    </div>
                    <div style="padding: 10px; background: #fef9c3; border-radius: 6px;">
                        <strong>风险等级接近率:</strong>
                        <div style="font-size: 18px; font-weight: bold; color: #ca8a04;">${levelCloseRatePercent}%</div>
                    </div>
                    <div style="padding: 10px; background: #e0f2fe; border-radius: 6px;">
                        <strong>关键因素匹配度:</strong>
                        <div style="font-size: 18px; font-weight: bold; color: #0369a1;">${factorOverlapPercent}%</div>
                    </div>
                    <div style="padding: 10px; background: #f3e8ff; border-radius: 6px;">
                        <strong>说明:</strong>
                        <div style="font-size: 11px; color: #7c3aed;">基于评估数据统计得出</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // 改进指标
    if (details.improvement) {
        html += `
            <div style="margin-bottom: 20px;">
                <h4 style="margin-bottom: 10px;">优化改进:</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div style="padding: 10px; background: #dcfce7; border-radius: 6px;">
                        <strong>置信度提升:</strong> +${details.improvement?.confidence_improvement_percent || 0}%
                    </div>
                    <div style="padding: 10px; background: #fce7f3; border-radius: 6px;">
                        <strong>预估准确率提升:</strong> +${details.improvement?.estimated_accuracy_improvement || 0}%
                    </div>
                </div>
            </div>
        `;
    }
    
    // 参数统计
    if (details.parameters?.post_training) {
        const postParams = details.parameters.post_training;
        html += `
            <div>
                <h4 style="margin-bottom: 10px;">模型参数:</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div style="padding: 10px; background: #f1f5f9; border-radius: 6px;">
                        <strong>总参数数量:</strong> ${postParams.total_parameters?.toLocaleString() || '-'}
                    </div>
                    <div style="padding: 10px; background: #f1f5f9; border-radius: 6px;">
                        <strong>可训练参数:</strong> ${postParams.trainable_parameters?.toLocaleString() || '-'}
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}



function renderKnowledgeGraphTree(node, container, level) {
    if (!node || !container) return;
    container.innerHTML = '';
    
    // 树状图实体类型中文名和图标
    const typeMeta = {
        '空域区域': { icon: '🏙', color: '#1a73e8' },
        '风险因素': { icon: '🟡', color: '#f9a825' },
        '基础设施': { icon: '🟢', color: '#43a047' },
        '敏感区域': { icon: '🔴', color: '#e53935' },
        '天气数据': { icon: '🔵', color: '#00acc1' },
        '法规手册': { icon: '📋', color: '#795548' }
    };
    
    function renderNode(n, lvl, parentEl) {
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'margin: 3px 0; margin-left: ' + (lvl * 20) + 'px;';
        
        const nodeEl = document.createElement('div');
        nodeEl.className = 'tree-node level-' + lvl;
        
        // 标题栏
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;gap:8px;';
        
        const icon = document.createElement('span');
        icon.style.cssText = 'font-size:14px;';
        icon.textContent = typeMeta[n.name]?.icon || '📌';
        
        const nameSpan = document.createElement('span');
        nameSpan.style.cssText = 'font-weight:600;';
        nameSpan.textContent = n.name;
        
        const countSpan = document.createElement('span');
        countSpan.style.cssText = 'font-size:11px;color:#888;';
        if (n.children && n.children.length > 0) {
            countSpan.textContent = '(' + n.children.length + '个)';
        }
        
        header.appendChild(icon);
        header.appendChild(nameSpan);
        header.appendChild(countSpan);
        nodeEl.appendChild(header);
        
        // 属性信息
        if (n.properties && Object.keys(n.properties).length > 0) {
            const propDiv = document.createElement('div');
            propDiv.style.cssText = 'font-size:11px;color:#666;margin-top:4px;padding-left:22px;';
            const propEntries = Object.entries(n.properties).slice(0, 5);
            propDiv.textContent = propEntries.map(([k, v]) => {
                const propNames = { 'weight': '权重', 'value': '风险值', 'infra_type': '类型', 'area_type': '类型', 'priority': '优先级' };
                return (propNames[k] || k) + ': ' + (typeof v === 'number' ? v.toFixed(2) : v);
            }).join(' | ');
            nodeEl.appendChild(propDiv);
        }
        
        wrapper.appendChild(nodeEl);
        parentEl.appendChild(wrapper);
        
        if (n.children && n.children.length > 0) {
            n.children.forEach(child => {
                renderNode(child, lvl + 1, parentEl);
            });
        }
    }
    
    renderNode(node, level, container);
}

async function startIteration() {
    const numIterations = prompt('请输入迭代轮数（默认3）:', '3');
    if (numIterations === null) return;
    
    const statusContainer = document.getElementById('iterationStatus');
    if (statusContainer) {
        statusContainer.innerHTML = '<p>正在自动生成数据集...</p>';
    }
    
    try {
        await generateRealDataset();
    } catch (e) {
        if (statusContainer) {
            statusContainer.innerHTML = '<p style="color:#dc2626;">数据集生成失败: ' + (e.message || '未知错误') + '</p>';
        }
        alert('数据集生成失败: ' + (e.message || '未知错误'));
        return;
    }
    
    try {
        const resp = await fetch('/enhanced/iteration/start', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({num_iterations: parseInt(numIterations) || 3})
        });
        
        const data = await resp.json();
        
        if (data.success) {
            alert('迭代训练已启动！');
            pollIterationStatus();
        } else {
            alert('启动失败: ' + (data.message || '未知错误'));
        }
    } catch (e) {
        alert('启动迭代训练出错: ' + (e.message || '未知错误'));
    }
}

async function stopIteration() {
    try {
        const resp = await fetch('/enhanced/iteration/stop', {
            method: 'POST',
            headers: {'Content-Type':'application/json'}
        });
        
        const data = await resp.json();
        alert(data.message || '停止成功');
        loadIterationStatus();
    } catch (e) {
        alert('停止迭代训练出错: ' + (e.message || '未知错误'));
    }
}

let pollInterval = null;

function pollIterationStatus() {
    if (pollInterval) clearInterval(pollInterval);
    
    pollInterval = setInterval(async function() {
        const status = await loadIterationStatus();
        if (status && !status.is_running) {
            clearInterval(pollInterval);
        }
    }, 3000);
}

async function loadIterationStatus() {
    const statusContainer = document.getElementById('iterationStatus');
    const historyContainer = document.getElementById('iterationHistory');
    
    try {
        const resp = await fetch('/enhanced/iteration/status', {
            method: 'POST',
            headers: {'Content-Type':'application/json'}
        });
        
        const status = await resp.json();
        
        let trainingStatusHtml = '';
        if (status.training_status) {
            const ts = status.training_status;
            const progressPercent = Math.round((ts.progress || 0) * 100);
            const statusText = getStatusText(ts.status);
            
            trainingStatusHtml = `
                <div style="margin-bottom: 15px; padding: 10px; background: #f0f9ff; border-radius: 6px; border-left: 3px solid #0ea5e9;">
                    <p><strong>训练状态:</strong> ${statusText}</p>
                    <p><strong>训练进度:</strong></p>
                    <div style="background: #e2e8f0; border-radius: 4px; height: 20px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #3b82f6, #0ea5e9); height: 100%; width: ${progressPercent}%; transition: width 0.3s ease;"></div>
                    </div>
                    <p style="margin-top: 5px; font-size: 14px; font-weight: 600;">${progressPercent}%</p>
                    ${ts.message ? `<p style="font-size: 13px; color: #475569; margin-top: 8px;"><strong>当前任务:</strong> ${ts.message}</p>` : ''}
                </div>
                <p><strong>本地模型:</strong> ${status.model_available_locally ? '✓ 已下载' : '✗ 未下载'}</p>
            `;
        }
        
        statusContainer.innerHTML = `
            <p><strong>系统状态:</strong> ${status.is_running ? '运行中' : '空闲'}</p>
            ${trainingStatusHtml}
            <p><strong>向量数据库文档数:</strong> ${status.vector_db_count || 0}</p>
            <p><strong>已训练模型数:</strong> ${(status.trained_models || []).length}</p>
        `;
        
        if (status.iteration_history && status.iteration_history.length > 0) {
            historyContainer.innerHTML = '<h4>最近迭代历史:</h4>';
            status.iteration_history.forEach(iter => {
                const item = document.createElement('div');
                item.style.padding = '10px';
                item.style.margin = '5px 0';
                item.style.background = 'white';
                item.style.borderRadius = '6px';
                item.style.borderLeft = iter.status === 'completed' ? '3px solid #22c55e' : 
                                        iter.status === 'error' ? '3px solid #ef4444' : '3px solid #eab308';
                item.innerHTML = `
                    <div><strong>第 ${iter.iteration_num} 轮</strong> - ${getIterationStatusText(iter.status)}</div>
                    <div style="font-size: 12px; color: #64748b;">
                        样本数: <strong style="color: #1e293b; font-size: 14px;">${iter.samples_count || 0}</strong> | 开始: ${iter.started_at}
                        ${iter.completed_at ? ` | 完成: ${iter.completed_at}` : ''}
                    </div>
                `;
                historyContainer.appendChild(item);
            });
        }
        
        return status;
    } catch (e) {
        statusContainer.innerHTML = '<p>加载状态失败: ' + (e.message || '未知错误') + '</p>';
        return null;
    }
}

function getStatusText(status) {
    const statusMap = {
        'idle': '空闲',
        'downloading': '下载中',
        'loading': '加载中',
        'training': '训练中',
        'completed': '已完成',
        'error': '出错'
    };
    return statusMap[status] || status;
}

function getIterationStatusText(status) {
    const statusMap = {
        'running': '运行中',
        'completed': '✓ 已完成',
        'error': '✗ 出错',
        'no_data': '无数据'
    };
    return statusMap[status] || status;
}

async function generateDynamicRoute() {
    const region = document.getElementById('routeRegionInput').value.trim() || '武汉';
    const container = document.getElementById('routeDisplay');
    
    container.innerHTML = '<p>生成中...</p>';
    
    try {
        const resp = await fetch('/enhanced/dynamic_route', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({region: region})
        });
        
        const route = await resp.json();
        
        let html = `<h4>${region} 动态评估路线</h4>`;
        html += `<p><strong>ID:</strong> ${route.id}</p>`;
        html += `<p><strong>使用工具:</strong> ${route.tools.join(', ')}</p>`;
        
        html += '<h5>风险因素权重:</h5>';
        html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">';
        Object.entries(route.factor_weights || {}).forEach(([name, weight]) => {
            html += `
                <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #3b82f6;">
                    <div style="font-weight: 600;">${name}</div>
                    <div style="color: #64748b;">权重: ${weight}%</div>
                </div>
            `;
        });
        html += '</div>';
        
        html += '<h5>工作流步骤:</h5>';
        (route.workflow_steps || []).forEach(step => {
            html += `
                <div class="route-step">
                    <div class="route-step-number">${step.step}</div>
                    <div>
                        <div style="font-weight: 600;">${step.action}</div>
                        <div style="font-size: 12px; color: #64748b;">工具: ${step.tool}</div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<p>生成动态路线失败: ' + e.message + '</p>';
    }
}

async function loadAssessmentHistoryNew() {
    const region = document.getElementById('historyRegionInput').value.trim();
    const container = document.getElementById('historyList');
    
    container.innerHTML = '<p>加载中...</p>';
    
    try {
        const resp = await fetch('/enhanced/assessment/history', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({region: region || null, limit: 50})
        });
        
        const history = await resp.json();
        
        if (history.length === 0) {
            container.innerHTML = '<p>暂无评估历史</p>';
            return;
        }
        
        container.innerHTML = '';
        history.forEach(item => {
            const itemEl = document.createElement('div');
            itemEl.className = 'history-item';
            itemEl.innerHTML = `
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">${item.region}</div>
                <div style="margin-bottom: 5px;">
                    <span style="background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600;">
                        ${item.risk_level}
                    </span>
                    <span style="margin-left: 10px; font-size: 12px; color: #64748b;">
                        ${item.created_at}
                    </span>
                </div>
                <div style="font-size: 13px; color: #374151;">${item.explanation || '无说明'}</div>
            `;
            container.appendChild(itemEl);
        });
    } catch (e) {
        container.innerHTML = '<p>加载评估历史失败: ' + e.message + '</p>';
    }
}

function showKnowledgeGraphView(viewType) {
    const treeContainer = document.getElementById('kgTreeContainer');
    const networkContainer = document.getElementById('kgNetworkContainer');
    
    if (viewType === 'tree') {
        treeContainer.style.display = 'block';
        networkContainer.style.display = 'none';
        if (currentKnowledgeGraphData && !treeContainer.querySelector('.tree-node')) {
            renderKnowledgeGraphTree(currentKnowledgeGraphData, treeContainer, 0);
        }
    } else {
        treeContainer.style.display = 'none';
        networkContainer.style.display = 'block';
        renderKnowledgeGraphNetworkModern();
    }
}

async function loadKnowledgeGraphNetwork(region) {
    try {
        const requestBody = region ? JSON.stringify({ region }) : '{}';
        const resp = await fetch('/knowledge_graph/visualize', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: requestBody
        });
        
        const data = await resp.json();
        if (data.success && data.knowledge_graph) {
            currentKnowledgeGraphData = data.knowledge_graph;
            return data.knowledge_graph;
        }
        return null;
    } catch (e) {
        console.error('加载知识图谱网络失败:', e);
        return null;
    }
}

const REL_TYPE_MAP = {
    'CONTAINS': '包含', 'INFLUENCES': '影响', 'ASSOCIATED_WITH': '关联',
    'ADJACENT_TO': '相邻', 'LOCATED_IN': '位于', 'GOVERNS': '管辖',
    'MONITORS': '监控', 'OPERATES_IN': '运行于', 'RESTRICTS': '限制',
    'DEPENDS_ON': '依赖于', 'APPLIES_TO': '适用于', 'RELATES_TO': '关联'
};

const ENTITY_TYPE_CONFIG = {
    'city':            { label: '城市/区域', color: '#1a73e8', icon: '●', shape: 'dot',     size: 28, priority: 6, clusterMin: 2 },
    'airspace_region': { label: '空域区域', color: '#1565c0', icon: '◉', shape: 'dot',     size: 26, priority: 6, clusterMin: 2 },
    'infrastructure':  { label: '基础设施', color: '#43a047', icon: '■', shape: 'square',  size: 20, priority: 4, clusterMin: 50 },
    'risk_factor':     { label: '风险因素', color: '#f9a825', icon: '▲', shape: 'triangle',size: 20, priority: 5, clusterMin: 20 },
    'sensitive_area':  { label: '敏感区域', color: '#e53935', icon: '◆', shape: 'diamond', size: 22, priority: 5, clusterMin: 50 },
    'subdistrict':     { label: '子区域',   color: '#7b1fa2', icon: '★', shape: 'star',    size: 18, priority: 3, clusterMin: 20 },
    'weather_data':    { label: '天气数据', color: '#00acc1', icon: '▼', shape: 'triangleDown', size: 16, priority: 2, clusterMin: 5 }
};

function entityTooltip(entity) {
    const props = entity.properties || {};
    const etype = entity.type || entity.entity_type || '';
    const cfg = ENTITY_TYPE_CONFIG[etype] || {};
    let parts = ['<div style="max-width:320px;font-size:13px;">'];
    parts.push('<b style="font-size:15px;">' + (entity.name || '未知') + '</b>');
    parts.push('<div style="color:#666;margin:2px 0;">类型: ' + (cfg.label || etype) + '</div>');
    
    const keyNames = {
        'weight': '权重', 'value': '风险值', 'factor_type': '因素类型',
        'infra_type': '设施类型', 'area_type': '区域类型', 'priority': '优先级',
        'population': '人口密度', 'location': '坐标', 'temperature': '温度',
        'wind_speed': '风速', 'visibility': '能见度', 'region_type': '区域级别',
        'elevation': '海拔', 'risk_level': '风险等级', 'status': '状态'
    };
    
    for (const [key, val] of Object.entries(props)) {
        if (key === 'importance' || key === 'entity_type') continue;
        let dv = val;
        if (typeof val === 'number') dv = val.toFixed(2);
        else if (Array.isArray(val)) dv = val.join(', ');
        else if (typeof val === 'object') dv = JSON.stringify(val);
        parts.push('<div><span style="color:#888;">' + (keyNames[key] || key) + ':</span> ' + dv + '</div>');
    }
    parts.push('</div>');
    return parts.join('');
}

function renderKnowledgeGraphNetworkModern() {
    const container = document.getElementById('kgNetworkContainer');
    container.innerHTML = '';
    
    if (!currentKnowledgeGraphData) {
        container.innerHTML = '<p style="padding:20px;text-align:center;">请先进行风险评估以生成知识图谱</p>';
        return;
    }
    
    const entities = currentKnowledgeGraphData.entities || [];
    const relations = currentKnowledgeGraphData.relations || [];
    console.log('知识图谱渲染 - 实体:', entities.length, '关系:', relations.length);
    
    const typeEntities = {};
    entities.forEach(e => {
        const t = e.type || e.entity_type || 'other';
        if (!typeEntities[t]) typeEntities[t] = [];
        typeEntities[t].push(e);
    });
    
    const topBar = document.createElement('div');
    topBar.style.cssText = 'position:absolute;top:10px;left:10px;right:10px;z-index:500;display:flex;gap:8px;align-items:center;flex-wrap:wrap;';
    
    let statsHTML = '<span style="background:rgba(255,255,255,0.95);padding:6px 12px;border-radius:6px;font-size:12px;font-weight:bold;box-shadow:0 1px 4px rgba(0,0,0,0.1);">';
    statsHTML += '实体: ' + entities.length + ' | 关系: ' + relations.length + '</span>';
    for (const [t, arr] of Object.entries(typeEntities)) {
        const cfg = ENTITY_TYPE_CONFIG[t] || {};
        statsHTML += '<span style="background:rgba(255,255,255,0.95);padding:4px 8px;border-radius:6px;font-size:11px;box-shadow:0 1px 4px rgba(0,0,0,0.1);color:' + cfg.color + ';">' + cfg.icon + ' ' + (cfg.label || t) + ': ' + arr.length + '</span>';
    }
    topBar.innerHTML = statsHTML;
    container.appendChild(topBar);
    
    const filterBar = document.createElement('div');
    filterBar.style.cssText = 'position:absolute;top:65px;left:10px;z-index:500;display:flex;flex-direction:column;gap:3px;background:rgba(255,255,255,0.95);padding:8px 10px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);font-size:11px;';
    filterBar.innerHTML = '<b style="margin-bottom:4px;">过滤类型</b>';
    for (const t of Object.keys(ENTITY_TYPE_CONFIG)) {
        const cfg = ENTITY_TYPE_CONFIG[t];
        const count = (typeEntities[t] || []).length;
        filterBar.innerHTML += '<label style="cursor:pointer;display:flex;align-items:center;gap:4px;white-space:nowrap;" id="kgFilter_' + t + '"><input type="checkbox" checked onchange="toggleKGEntityType(\'' + t + '\', this.checked)" style="margin:0;"> <span style="color:' + cfg.color + ';">' + cfg.icon + '</span> ' + cfg.label + ' (' + count + ')</label>';
    }
    filterBar.innerHTML += '<button onclick="expandAllKGClusters()" style="margin-top:6px;padding:3px 8px;font-size:11px;border:1px solid #ccc;border-radius:4px;background:#fff;cursor:pointer;">展开全部</button>';
    filterBar.innerHTML += '<button onclick="collapseAllKGClusters()" style="padding:3px 8px;font-size:11px;border:1px solid #ccc;border-radius:4px;background:#fff;cursor:pointer;">折叠全部</button>';
    container.appendChild(filterBar);
    
    const searchBar = document.createElement('div');
    searchBar.style.cssText = 'position:absolute;top:65px;right:10px;z-index:500;';
    searchBar.innerHTML = '<input id="kgSearchInput" type="text" placeholder="搜索节点..." oninput="searchKGNode(this.value)" style="padding:6px 12px;border:1px solid #ccc;border-radius:6px;font-size:13px;width:180px;box-shadow:0 1px 4px rgba(0,0,0,0.1);"> <span id="kgSearchResult" style="font-size:11px;color:#666;margin-left:4px;"></span>';
    container.appendChild(searchBar);
    
    const networkDiv = document.createElement('div');
    networkDiv.id = 'kgNetworkInner2';
    networkDiv.style.cssText = 'width:100%;height:100%;';
    container.appendChild(networkDiv);
    
    const nodeIds = new Set();
    const nodesArr = [];
    
    entities.forEach((entity, index) => {
        const nodeId = entity.id || 'entity_' + index;
        nodeIds.add(nodeId);
        const etype = entity.type || entity.entity_type || '';
        const cfg = ENTITY_TYPE_CONFIG[etype] || ENTITY_TYPE_CONFIG['infrastructure'];
        
        nodesArr.push({
            id: nodeId,
            label: entity.name || '节点' + index,
            title: entityTooltip(entity),
            color: { background: cfg.color, border: '#333', highlight: { background: cfg.color, border: '#000' } },
            shape: cfg.shape,
            size: cfg.size,
            font: { size: 12, face: 'Microsoft YaHei, sans-serif', color: '#333' },
            borderWidth: 2,
            borderWidthSelected: 4,
            group: etype,
            _etype: etype,
            hidden: false
        });
    });
    
    const edgeArr = [];
    relations.forEach((rel, index) => {
        const sid = rel.source || rel.source_id;
        const tid = rel.target || rel.target_id;
        if (nodeIds.has(sid) && nodeIds.has(tid)) {
            const rtype = rel.type || rel.relation_type || '';
            const rlabel = REL_TYPE_MAP[rtype] || rtype;
            edgeArr.push({
                id: 'edge_' + index,
                from: sid,
                to: tid,
                label: rlabel,
                arrows: 'to',
                font: { size: 9, align: 'middle', face: 'Microsoft YaHei, sans-serif' },
                width: 1.2,
                color: { color: '#bcc', highlight: '#2196F3', hover: '#2196F3' },
                smooth: { type: 'continuous', roundness: 0.5 }
            });
        }
    });
    
    if (nodesArr.length === 0) {
        container.innerHTML = '<p style="padding:20px;text-align:center;">知识图谱暂无数据</p>';
        return;
    }
    
    const nodeDataset = new vis.DataSet(nodesArr);
    const edgeDataset = new vis.DataSet(edgeArr);
    
    const network = new vis.Network(networkDiv, { nodes: nodeDataset, edges: edgeDataset }, {
        nodes: { borderWidth: 2, borderWidthSelected: 4, shadow: { enabled: true, size: 4 } },
        edges: {
            width: 1.0,
            color: { color: '#bcc', highlight: '#2196F3', hover: '#2196F3', inherit: false },
            smooth: { type: 'continuous', forceDirection: 'none', roundness: 0.5 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } }
        },
        physics: {
            enabled: true,
            solver: 'barnesHut',
            barnesHut: { gravitationalConstant: -5000, centralGravity: 0.5, springLength: 120, springConstant: 0.02, damping: 0.09 },
            stabilization: { enabled: true, iterations: 500, updateInterval: 25, fit: false }
        },
        interaction: {
            hover: true,
            tooltipDelay: 150,
            navigationButtons: true,
            keyboard: true,
            zoomView: true,
            dragView: true
        },
        layout: { improvedLayout: true, randomSeed: 42 }
    });
    
    network._nodeDataset = nodeDataset;
    network._edgeDataset = edgeDataset;
    network._entities = entities;
    network._typeEntities = typeEntities;
    window._kgNetwork = network;
    
    console.log('节点总数:', nodesArr.length, '条边总数:', edgeArr.length);
    
    network.on('doubleClick', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            if (network.isCluster(nodeId)) {
                network.openCluster(nodeId);
            } else {
                const node = nodeDataset.get(nodeId);
                if (node && node.title) {
                    let panel = document.getElementById('kgDetailPanel2');
                    if (panel) panel.remove();
                    panel = document.createElement('div');
                    panel.id = 'kgDetailPanel2';
                    panel.style.cssText = 'position:absolute;top:10px;right:10px;z-index:600;background:white;padding:14px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.2);max-width:340px;max-height:460px;overflow-y:auto;font-size:13px;';
                    panel.innerHTML = node.title + '<button onclick="this.parentElement.remove()" style="position:absolute;top:6px;right:8px;background:none;border:none;font-size:18px;cursor:pointer;color:#999;">x</button>';
                    container.appendChild(panel);
                }
            }
        }
    });
    
    network.once('stabilizationIterationsDone', function() {
        network.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
    });
    
    network.fit({ animation: { duration: 400 } });
    console.log('知识图谱渲染完成: ' + nodesArr.length + ' 节点, ' + edgeArr.length + ' 边');
    
    window._openAllClusters = function() {
        const allNodeIds = nodeDataset.getIds();
        allNodeIds.forEach(id => { if (network.isCluster(id)) network.openCluster(id); });
    };
}

function clusterByType(network, nodeDataset) {
    const allNodes = nodeDataset.get();
    const groupMap = {};
    allNodes.forEach(n => {
        const g = n._etype || n.group || 'other';
        if (!groupMap[g]) groupMap[g] = [];
        groupMap[g].push(n.id);
    });
    
    for (const [gtype, nodeIds] of Object.entries(groupMap)) {
        const cfg = ENTITY_TYPE_CONFIG[gtype];
        const min = cfg ? cfg.clusterMin : 5;
        if (nodeIds.length >= min) {
            try {
                network.cluster({
                    joinCondition: function(n) { return nodeIds.includes(n.id); },
                    clusterNodeProperties: {
                        label: (cfg ? cfg.label : gtype) + ' (' + nodeIds.length + ')',
                        shape: 'dot',
                        size: 35,
                        color: { background: cfg ? cfg.color : '#888', border: '#333' },
                        font: { size: 16, face: 'Microsoft YaHei, sans-serif', color: '#fff' },
                        borderWidth: 3
                    }
                });
            } catch(e) {}
        }
    }
}

function toggleKGEntityType(etype, show) {
    const network = window._kgNetwork;
    if (!network || !network._nodeDataset) return;
    const allNodes = network._nodeDataset.get();
    const updates = [];
    
    allNodes.forEach(n => {
        if (n._etype === etype || n.group === etype) {
            if (show && n.hidden) {
                network._nodeDataset.update({ id: n.id, hidden: false });
            } else if (!show) {
                network._nodeDataset.update({ id: n.id, hidden: true });
            }
        }
    });
}

function searchKGNode(query) {
    const network = window._kgNetwork;
    const resultSpan = document.getElementById('kgSearchResult');
    if (!network || !network._nodeDataset) {
        if (resultSpan) resultSpan.textContent = '';
        return;
    }
    
    query = query.trim().toLowerCase();
    if (!query) {
        if (resultSpan) resultSpan.textContent = '';
        network.unselectAll();
        return;
    }
    
    const allNodes = network._nodeDataset.get();
    let found = null;
    for (const n of allNodes) {
        const label = (n.label || '').toLowerCase();
        const props = JSON.stringify(n.title || '').toLowerCase();
        if (label.includes(query) || props.includes(query)) {
            found = n.id;
            break;
        }
    }
    
    if (found) {
        if (resultSpan) resultSpan.textContent = '已找到';
        if (network.isCluster(found)) network.openCluster(found);
        network.selectNodes([found]);
        network.focus(found, { animation: { duration: 500 }, scale: 1.5 });
    } else {
        if (resultSpan) resultSpan.textContent = '未找到';
        network.unselectAll();
    }
}

function expandAllKGClusters() {
    const network = window._kgNetwork;
    if (!network) return;
    const nodeDataset = network._nodeDataset || network.body.data.nodes;
    const allIds = nodeDataset.getIds();
    allIds.forEach(id => {
        if (network.isCluster(id)) network.openCluster(id);
    });
}

function collapseAllKGClusters() {
    const network = window._kgNetwork;
    if (!network) return;
    clusterByType(network, network._nodeDataset);
}

// 重写loadKnowledgeGraph函数
const loadKnowledgeGraph = async function(region) {
    const treeContainer = document.getElementById('kgTreeContainer');
    treeContainer.innerHTML = '<p>加载中...</p>';
    try {
        await loadKnowledgeGraphNetwork(region);
        const requestBody = region ? JSON.stringify({ region }) : '{}';
        const resp = await fetch('/enhanced/kg_tree', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: requestBody
        });
        const data = await resp.json();
        renderKnowledgeGraphTree(data, treeContainer, 0);
        showKnowledgeGraphView('network');
    } catch (e) {
        treeContainer.innerHTML = '<p>加载知识图谱失败: ' + e.message + '</p>';
    }
};

async function generateRealDataset() {
    const container = document.getElementById('datasetInfoDisplay');
    if (!container) return;
    
    container.innerHTML = '<p>正在生成数据集...</p>';
    
    try {
        const resp = await fetch('/train/generate_dataset', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({})
        });
        
        const data = await resp.json();
        
        if (data.success) {
            let riskDistHtml = '';
            if (data.risk_distribution) {
                riskDistHtml = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:8px;">';
                for (const [level, count] of Object.entries(data.risk_distribution)) {
                    let bgColor = '#f9fafb';
                    let borderColor = '#e5e7eb';
                    if (level.includes('高')) { bgColor = '#fef2f2'; borderColor = '#fecaca'; }
                    else if (level.includes('中')) { bgColor = '#fff7ed'; borderColor = '#fed7aa'; }
                    else { bgColor = '#f0fdf4'; borderColor = '#bbf7d0'; }
                    riskDistHtml += `<div style="padding:6px;background:${bgColor};border-radius:4px;border:1px solid ${borderColor};"><div style="font-weight:600;font-size:12px;">${level}</div><div style="font-size:16px;font-weight:bold;">${count}</div></div>`;
                }
                riskDistHtml += '</div>';
            }
            
            container.innerHTML = `
                <div style="padding:10px;background:#f0fdf4;border-radius:6px;margin-bottom:10px;">
                    <strong>数据集生成成功!</strong>
                    <div style="font-size:12px;color:#64748b;margin-top:4px;">文件: ${data.filepath}</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #3b82f6;">
                        <div style="font-size:11px;color:#64748b;">总样本数</div>
                        <div style="font-size:20px;font-weight:bold;color:#1e40af;">${data.total_samples || 0}</div>
                    </div>
                    <div style="padding:8px;background:white;border-radius:6px;border-left:3px solid #10b981;">
                        <div style="font-size:11px;color:#64748b;">城市数量</div>
                        <div style="font-size:20px;font-weight:bold;color:#065f46;">${data.city_count || 0}</div>
                    </div>
                </div>
                ${riskDistHtml}
                <div style="margin-top:8px;padding:8px;background:white;border-radius:6px;font-size:11px;color:#64748b;">
                    <strong>数据来源:</strong> 中国统计年鉴2023、中国气象局、民航局公开数据、高德地图API
                </div>
            `;
        } else {
            container.innerHTML = '<p style="color:#dc2626;">生成失败: ' + (data.error || '未知错误') + '</p>';
        }
    } catch (e) {
        container.innerHTML = '<p style="color:#dc2626;">生成失败: ' + e.message + '</p>';
    }
}
