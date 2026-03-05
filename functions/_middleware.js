// functions/_middleware.js
export async function onRequest(context) {
  const { request, next } = context;
  
  // 获取原始响应
  const response = await next();
  
  // 检查是否是 .txt 文件
  const url = new URL(request.url);
  if (url.pathname.endsWith('.txt')) {
    // 创建新响应
    const newResponse = new Response(response.body, response);
    
    // 强制设置编码
    newResponse.headers.set('Content-Type', 'text/plain; charset=utf-8');
    
    // 删除可能干扰的压缩头
    newResponse.headers.delete('Content-Encoding');
    newResponse.headers.delete('Content-Length'); // 让浏览器重新计算
    
    return newResponse;
  }
  
  return response;
}
