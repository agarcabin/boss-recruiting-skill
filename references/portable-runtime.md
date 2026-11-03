# 独立环境

首次安装执行官方可信scripts/bootstrap.ps1。依赖位于references/runtime-lock.json，由脚本内置摘要认证；Python固定Windows x64官方构建，所有wheel固定版本、文件、官方URL和SHA-256，安装使用--no-index --require-hashes。OCR模型包含在固定rapidocr轮子中，不在线自动追随模型更新。缓存避免重复下载，可用的既有环境保留。

环境探测包含SSL、Tk、cryptography、openpyxl、pypdf、RapidOCR、ONNX Runtime、OpenCV、NumPy和三份本地ONNX模型。安装完成后用runtime/win-x64/python/python.exe执行脚本。需要诊断时运行scripts/verify_runtime.ps1 -Json；正常招呼不重复环境测试。

环境和依赖不进Git或Release。可在引导时指定TargetRoot/CacheRoot；长路径文件复制使用Windows扩展路径，环境只安装当前用户目录，不修改系统Python或PATH。无网络且缓存不完整时明确失败，不跳过哈希或签名校验。
