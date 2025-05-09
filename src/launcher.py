# 파일 위치: loss_recovery_ui/src/launcher.py
import subprocess
from pathlib import Path
import os
import sys

if __name__ == '__main__':
    # 이 launcher.py 파일이 있는 디렉토리 (src)
    src_dir = Path(__file__).parent.resolve()

    # 실행하려는 패키지 이름
    package_name = "loss_recovery_pro"

    # 패키지 내의 메인 애플리케이션 모듈 (app.py)
    # streamlit run 명령어는 이 경로를 src_dir 기준으로 찾게 됨
    app_module_relative_path = f"{package_name}/app.py"

    # PYTHONPATH에 src 디렉토리의 부모 디렉토리를 추가하여
    # loss_recovery_pro 패키지를 찾을 수 있도록 함.
    # 이렇게 하면 streamlit 내부에서 from loss_recovery_pro.app_state 등을 찾을 수 있음.
    # (주의: streamlit run 자체가 이를 잘 처리할 수도 있으므로, 이 부분이 항상 필요한 것은 아님)
    # project_root = src_dir.parent
    # current_python_path = os.environ.get("PYTHONPATH", "")
    # env = os.environ.copy()
    # env["PYTHONPATH"] = f"{project_root}{os.pathsep}{current_python_path}"
    # print(f"Launcher: Setting PYTHONPATH to include {project_root}")
    # print(f"Launcher: Running streamlit with cwd={src_dir}")

    # streamlit run 명령어 실행
    # cwd를 src 디렉토리로 설정하면, streamlit이 loss_recovery_pro/app.py를
    # 패키지 내의 모듈로 인식할 가능성이 높아짐.
    try:
        # streamlit이 실행할 스크립트의 경로 (src 디렉토리 기준)
        # 예: loss_recovery_pro/app.py
        # 실행: streamlit run src/loss_recovery_pro/app.py (프로젝트 루트에서 실행하는 효과)
        # 또는 cwd를 src로 하고 streamlit run loss_recovery_pro/app.py
        # 여기서는 launcher가 src에 있으므로, src를 cwd로.
        subprocess.run(
            ["streamlit", "run", app_module_relative_path],
            cwd=src_dir, # 작업 디렉토리를 src로 설정
            check=True,  # 오류 발생 시 예외 발생
            # env=env # PYTHONPATH를 명시적으로 설정할 경우
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit app: {e}")
    except FileNotFoundError:
        print("Error: streamlit command not found. Make sure Streamlit is installed and in your PATH.")