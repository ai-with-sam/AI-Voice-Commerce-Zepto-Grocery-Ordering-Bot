import sys
import json
from automation.zepto_bot1 import process_voice_file

file_path = sys.argv[1]

result = process_voice_file(file_path)

print(json.dumps(result))