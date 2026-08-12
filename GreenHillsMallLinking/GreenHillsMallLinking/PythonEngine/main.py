import argparse
import sys
import paradox_sync
import eod_generator
import xml_sync

def main():
    parser = argparse.ArgumentParser(description="Main Engine Bridge")
    parser.add_argument("--action", type=str, required=True,
                         help="Action: 'sync', 'sync_cloud', or 'process_eod'")
    parser.add_argument("--db", type=str, required=True, help="Path to SQLite DB")
    parser.add_argument("--paradox_dir", type=str, default="", help="Path to Paradox files directory")
    parser.add_argument("--password", type=str, default=paradox_sync.DB_PASSWORD, help="Paradox Password")
    parser.add_argument("--target_date", type=str, default="", help="Target date (YYYY-MM-DD) for process_eod")
    parser.add_argument("--export_dir", type=str, default="", help="Output folder for the .SALE export file")
    parser.add_argument("--cloud_dir", type=str, default="", help="Path to cloud XML export folder")
    parser.add_argument("--source", type=str, default="paradox",
                         help="Data source for process_eod: 'paradox' or 'cloud'")

    args, _ = parser.parse_known_args()

    if args.action in ["sync", "sync_paradox"]:
        if not args.paradox_dir:
            print("ERROR: --paradox_dir is required for sync action.", file=sys.stderr)
            sys.exit(1)

        print("Starting Paradox Backup Sync...")
        print(f"DB Path: {args.db}")
        print(f"Paradox Folder: {args.paradox_dir}")

        success = paradox_sync.sync_paradox(args.db, args.paradox_dir, password=args.password)
        if not success:
            sys.exit(1)

    elif args.action == "sync_cloud":
        if not args.cloud_dir:
            print("ERROR: --cloud_dir is required for sync_cloud action.", file=sys.stderr)
            sys.exit(1)

        print("Starting Cloud XML Sync...")
        print(f"DB Path: {args.db}")
        print(f"Cloud Folder: {args.cloud_dir}")
        print(f"Target Date: {args.target_date or '(none - full rebuild)'}")

        success = xml_sync.sync_cloud_xml(args.db, args.cloud_dir, target_date=args.target_date or None)
        if not success:
            sys.exit(1)

    elif args.action in ["process_eod", "eod"]:
        if not args.target_date:
            print("ERROR: --target_date is required for process_eod action.", file=sys.stderr)
            sys.exit(1)
        if not args.export_dir:
            print("ERROR: --export_dir is required for process_eod action.", file=sys.stderr)
            sys.exit(1)

        print("Starting EOD Generation...")
        print(f"DB Path: {args.db}")
        print(f"Target Date: {args.target_date}")
        print(f"Export Folder: {args.export_dir}")
        print(f"Source: {args.source}")

        success = eod_generator.generate_eod(args.db, args.target_date, args.export_dir, source=args.source)
        if not success:
            sys.exit(1)

    else:
        print(f"ERROR: Unknown action '{args.action}'.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()