@echo off
REM ============================================================
REM  316LN 三维高温蠕变场预测器 - 一键启动
REM  STEP22: 启动后端(:5000) + 前端(:5173)，浏览器自动打开
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  ============================================
echo   316LN 三维高温蠕变场预测器 启动中...
echo  ============================================
echo.

REM ---- 启动后端（后台窗口） ----
echo  [1/3] 启动预测后端 :5000 ...
start "316LN-Backend" cmd /k "ml\.venv\Scripts\python.exe webapp\backend\app.py"

REM ---- 等待后端就绪 ----
echo  [2/3] 等待后端就绪...
timeout /t 4 /nobreak >nul

REM ---- 启动前端（后台窗口） ----
echo  [3/3] 启动前端 :5173 ...
start "316LN-Frontend" cmd /k "cd webapp\frontend && npm run dev -- --host 127.0.0.1"

timeout /t 4 /nobreak >nul
echo.
echo  ============================================
echo   浏览器打开: http://127.0.0.1:5173
echo   页面顶部切换到 [V1.3 多物理场] 标签
echo   （默认 V1.2 模式保持不变）
echo   关闭窗口 = 停止服务
echo  ============================================
start http://127.0.0.1:5173
echo.
echo  启动完成。关闭这两个黑色窗口即可停止服务。
pause >nul
