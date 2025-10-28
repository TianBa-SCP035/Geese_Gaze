from flask import Flask, request, jsonify
import os
from datetime import datetime
import random

app = Flask(__name__)

# 存储接收到的数据
received_data = []

@app.route('/api/qr_results', methods=['POST'])
def receive_qr_results():
    """接收二维码识别结果的接口"""
    try:
        data = request.json
        
        # 添加接收时间戳
        data['received_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 存储数据
        received_data.append(data)
        
        # 打印接收到的数据
        print(f"接收到二维码识别结果: {data}")
        
        # 获取results中的所有键
        results_keys = list(data.get('results', {}).keys())
        
        # 随机选择5个键作为negative
        negative = random.sample(results_keys, min(5, len(results_keys))) if results_keys else []
        
        # 随机选择5个键作为loc_err，确保有2个与negative重复
        if len(results_keys) >= 5:
            # 从negative中随机选择2个
            common_keys = random.sample(negative, 2) if len(negative) >= 2 else negative
            # 从剩余键中选择3个
            remaining_keys = [k for k in results_keys if k not in common_keys]
            additional_keys = random.sample(remaining_keys, 3) if len(remaining_keys) >= 3 else remaining_keys
            loc_err = common_keys + additional_keys
        else:
            # 如果键不足5个，使用所有键
            loc_err = results_keys.copy()
        
        # 检查请求中是否包含data_id
        request_data_id = data.get('data_id')
        response_data_id = request_data_id if request_data_id is not None else len(received_data)
        
        # 返回成功响应
        return jsonify({
            'status': 'success',
            'message': '二维码识别结果已接收',
            'data_id': response_data_id,
            'negative': negative,
            'loc_err': loc_err
        }), 200
        
    except Exception as e:
        print(f"处理请求时出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'处理请求时出错: {str(e)}'
        }), 500

@app.route('/api/qr_results', methods=['GET'])
def get_received_data():
    """获取已接收的数据列表"""
    return jsonify({
        'status': 'success',
        'count': len(received_data),
        'data': received_data
    }), 200

@app.route('/api/qr_results/clear', methods=['POST'])
def clear_received_data():
    """清空已接收的数据"""
    global received_data
    received_data = []
    return jsonify({
        'status': 'success',
        'message': '数据已清空'
    }), 200

@app.route('/', methods=['GET'])
def index():
    """简单的首页"""
    return """
    <html>
        <head>
            <title>二维码识别结果接收服务</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                .section { margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                button { padding: 8px 15px; margin: 5px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background-color: #45a049; }
                pre { background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>二维码识别结果接收服务</h1>
                
                <div class="section">
                    <h2>API接口</h2>
                    <p><strong>POST /api/qr_results</strong> - 接收二维码识别结果</p>
                    <p><strong>GET /api/qr_results</strong> - 获取已接收的数据</p>
                    <p><strong>POST /api/qr_results/clear</strong> - 清空已接收的数据</p>
                </div>
                
                <div class="section">
                    <h2>操作</h2>
                    <button onclick="refreshData()">刷新数据</button>
                    <button onclick="clearData()">清空数据</button>
                    <div id="data-container"></div>
                </div>
            </div>
            
            <script>
                function refreshData() {
                    fetch('/api/qr_results')
                        .then(response => response.json())
                        .then(data => {
                            let container = document.getElementById('data-container');
                            container.innerHTML = `<h3>已接收 ${data.count} 条数据</h3>`;
                            
                            if (data.data && data.data.length > 0) {
                                data.data.forEach((item, index) => {
                                    container.innerHTML += `
                                        <div class="section">
                                            <h4>数据 #${index + 1} (接收时间: ${item.received_at})</h4>
                                            <pre>${JSON.stringify(item, null, 2)}</pre>
                                        </div>
                                    `;
                                });
                            }
                        })
                        .catch(error => {
                            console.error('获取数据失败:', error);
                            document.getElementById('data-container').innerHTML = '<p>获取数据失败</p>';
                        });
                }
                
                function clearData() {
                    fetch('/api/qr_results/clear', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            refreshData();
                        })
                        .catch(error => {
                            console.error('清空数据失败:', error);
                            alert('清空数据失败');
                        });
                }
                
                // 页面加载时刷新数据
                window.onload = refreshData;
            </script>
        </body>
    </html>
    """

if __name__ == '__main__':
    print("启动二维码识别结果接收服务...")
    print("访问 http://127.0.0.1:5000 查看接收的数据")
    app.run(host='0.0.0.0', port=5000, debug=True)