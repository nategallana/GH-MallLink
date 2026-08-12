import argparse
import sys
import paradox_sync

def main():
    parser = argparse.ArgumentParser(description="Main Engine Bridge")
    parser.add_argument("--action", type=str, required=True, help="Action: 'sync' or 'process_eod'")
    parser.add_argument("--db", type=str, required=True, help="Path to SQLite DB")
    # Set default="" so process_eod doesn't fail when --paradox_dir isn't supplied
    parser.add_argument("--paradox_dir", type=str, default="", help="Path to Paradox files directory")
    parser.add_argument("--password", type=str, default=paradox_sync.DB_PASSWORD, help="Paradox Password")

    args, _ = parser.parse_known_args()

    if args.action in ["sync", "sync_paradox"]:
        if not args.paradox_dir:
            print("ERROR: --paradox_dir is required for sync action.", file=sys.stderr)
            sys.exit(1)
            
        print("Starting Paradox Sync...")
        print(f"DB Path: {args.db}")
        print(f"Paradox Folder: {args.paradox_dir}")
        
        success = paradox_sync.sync_paradox(args.db, args.paradox_dir, args.password)
        if not success:
            sys.exit(1)

    elif args.action == "process_eod":
        # Call your EOD generation logic here
        pass

if __name__ == "__main__":
    main()