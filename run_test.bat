@echo off
REM ============================================
REM 香港法律知识图谱 - 快速启动脚本
REM ============================================

echo.
echo ============================================
echo   香港法律知识图谱 - 测试启动
echo ============================================
echo.
echo 请选择测试方式：
echo.
echo [1] 检查依赖
echo [2] 运行7步架构测试
echo [3] 处理input目录中的PDF（不使用Neo4j）
echo [4] 处理input目录中的PDF（使用Neo4j）
echo [5] 查看测试指南
echo.
set /p choice=请输入选项 (1-5): 

if "%choice%"=="1" goto check_deps
if "%choice%"=="2" goto test_7step
if "%choice%"=="3" goto process_pdf_no_neo4j
if "%choice%"=="4" goto process_pdf_with_neo4j
if "%choice%"=="5" goto show_guide
goto invalid

:check_deps
echo.
echo ============================================
echo   正在检查依赖...
echo ============================================
echo.
python test_dependencies.py
echo.
echo 按任意键返回主菜单...
pause >nul
goto start

:test_7step
echo.
echo ============================================
echo   正在运行7步架构测试...
echo ============================================
echo.
python test_7_step_pipeline.py
echo.
echo 按任意键返回主菜单...
pause >nul
goto start

:process_pdf_no_neo4j
echo.
echo ============================================
echo   正在处理PDF（不使用Neo4j）...
echo ============================================
echo.
python main.py --no-neo4j
echo.
echo 按任意键返回主菜单...
pause >nul
goto start

:process_pdf_with_neo4j
echo.
echo ============================================
echo   正在处理PDF（使用Neo4j）...
echo ============================================
echo.
python main.py
echo.
echo 按任意键返回主菜单...
pause >nul
goto start

:show_guide
echo.
echo ============================================
echo   打开测试指南...
echo ============================================
echo.
start TESTING.md
goto start

:invalid
echo.
echo ============================================
echo   无效选项，请重新选择
echo ============================================
echo.
pause
goto start

:start
cls
goto :eof
