#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pkgpicker.ui_app import PkgPickerApp

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="packages.json")
    args = ap.parse_args()
    PkgPickerApp(data_path=args.data).run()

if __name__ == "__main__":
    main()

