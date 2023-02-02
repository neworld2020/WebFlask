# get current path
sh_path=$(cd "$(dirname "$0")" || exit; pwd)

# install packages
pip install -r "$sh_path/requirements.txt"

# run
pytest "$sh_path/../app.py" "$sh_path/test_api.py" --html "$sh_path/../report/result.html"