"""
Smaže duplicitní drafty a problematické adresy.
Nechá vždy první výskyt každé adresy, smaže zbytek.
"""
from gmail_draft import get_gmail_service

PROBLEMATIC = {"vasemail@domena.cz", "zakaznici@foodora.cz"}


def get_draft_to(service, draft_id):
    draft = service.users().drafts().get(userId="me", id=draft_id, format="metadata").execute()
    headers = draft["message"].get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "To":
            return h["value"]
    return None


def main():
    service = get_gmail_service()

    resp = service.users().drafts().list(userId="me").execute()
    drafts = resp.get("drafts", [])
    while "nextPageToken" in resp:
        resp = service.users().drafts().list(userId="me", pageToken=resp["nextPageToken"]).execute()
        drafts.extend(resp.get("drafts", []))

    print(f"Celkem draftů: {len(drafts)}\n")

    seen = {}
    to_delete = []

    for draft in drafts:
        draft_id = draft["id"]
        to = get_draft_to(service, draft_id)

        if to in PROBLEMATIC:
            to_delete.append((draft_id, to, "problematická adresa"))
        elif to in seen:
            to_delete.append((draft_id, to, "duplicita"))
        else:
            seen[to] = draft_id

    print(f"K smazání: {len(to_delete)}")
    for draft_id, to, reason in to_delete:
        print(f"  [{reason}] {to}")

    print()
    confirm = input(f"Smazat {len(to_delete)} draftů? (ano/ne): ")
    if confirm.strip().lower() != "ano":
        print("Zrušeno.")
        return

    for draft_id, to, reason in to_delete:
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        print(f"  Smazán: {to}")

    print(f"\nHotovo. Zbývá {len(seen)} unikátních draftů.")


if __name__ == "__main__":
    main()
