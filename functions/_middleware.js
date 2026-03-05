// functions/_middleware.js
export async function onRequest(context) {
  const { request, next } = context;
  
  // 获取原始响应
  const response = await next();
  
  // 检查是否是 .txt 文件
  const url = new URL(request.url);
  if (url.pathname.endsWith('.txt')) {
    // 修改响应头，强制使用 UTF-8 编码
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('Content-Type', 'text/plain; charset=utf-8');
    return newResponse;
  }
  
  // 如果不是 txt 文件，直接返回原响应
  return response;
}
