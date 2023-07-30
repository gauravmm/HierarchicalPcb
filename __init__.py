import traceback
from pathlib import Path

with Path("C:\\Users\\User\\Desktop\\hierarchical.log").open("w") as f:
    f.write("Hello World\n")
    try:
        from .hplugin import HierarchicalPCBPlugin

        HierarchicalPCBPlugin().register()

    except Exception as e:
        f.write(str(e))
        f.write(traceback.format_exc())
    finally:
        f.write("Goodbye World\n")
