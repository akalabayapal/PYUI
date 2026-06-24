import subprocess
from pathlib import Path

def build_global_tailwind(tailwind_exe, html_dir, output_css, temp_css="temp.css"):
    # 1. Resolve everything into pure, absolute system paths
    exe_path = Path(tailwind_exe).resolve()
    out_path = Path(output_css).resolve()
    tmp_css_path = Path(temp_css).resolve()
    base_html_dir = Path(html_dir).resolve()

    # 2. Format the directory string with forward slashes for Tailwind's config parser
    safe_dir_path = str(base_html_dir).replace("\\", "/")

    # 3. FIX: Write the directory search path directly inside the CSS file!
    # This bypasses the buggy CLI command-line argument reader entirely.
    css_content = f'''@import "tailwindcss";
@source "{safe_dir_path}/**/*.html";
'''
    tmp_css_path.write_text(css_content, encoding="utf-8")

    # 4. Clean command WITHOUT the problematic --content flag
    cmd = [
        str(exe_path),
        "-i", str(tmp_css_path),
        "--minify"
    ]

    print(f"[TAILWIND BUILD] Configured @source pathway:\n{css_content}")
    print(f"[TAILWIND BUILD] Running: {' '.join(cmd)}")

    # 5. Stream stdout straight to file to dodge OneDrive/Windows folder permission bugs
    with open(out_path, "w", encoding="utf-8") as out_file:
        subprocess.run(cmd, stdout=out_file, check=True)
        
    # Clean up tracking configuration file
    if tmp_css_path.exists():
        tmp_css_path.unlink()
        
    return True
