
def confirm_save_redo_cancel():
    while True:
        ans = input("Save (s), redo (r), cancel (c)? [s]: ").strip().lower()

        if ans == "":
            return "s"

        if ans in ("s", "r", "c"):
            return ans

        print("Enter s, r, or c.")
