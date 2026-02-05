
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

print(f"Path: {sys.path}")
try:
    import v2.zoning_fixer
    print("Success: import v2.zoning_fixer")
except ImportError as e:
    print(f"Error: {e}")

try:
    from v2.zoning_fixer import fix_zoning
    print("Success: from v2.zoning_fixer import fix_zoning")
except ImportError as e:
    print(f"Error: {e}")
