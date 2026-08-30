import argparse
import json

from database import connect, initialise_database
from player_database import load_players
from recommendation_engine import get_recommendations


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Replay historical recommendation decisions "
            "from a stored draft session."
        )
    )

    parser.add_argument(
        "session_id",
        type=int,
        help="Draft session ID to replay",
    )

    parser.add_argument(
        "target_picks",
        type=int,
        nargs="+",
        help="Overall draft pick(s) to replay",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    session_id = args.session_id
    target_picks = sorted(set(args.target_picks))

    initialise_database()
    players = load_players()

    with connect() as db:
        session = db.execute(
            """
            SELECT
                ds.id,
                ds.name,
                ds.session_type,
                ds.teams,
                ds.your_slot,
                s.season
            FROM draft_sessions ds
            JOIN seasons s
              ON s.id = ds.season_id
            WHERE ds.id = ?
            """,
            (session_id,),
        ).fetchone()

        if session is None:
            raise SystemExit(
                f"Draft session {session_id} not found"
            )

        rows = db.execute(
            """
            SELECT
                overall_pick,
                round_number,
                slot,
                is_yours,
                player_json
            FROM draft_picks
            WHERE draft_session_id = ?
            ORDER BY overall_pick
            """,
            (session_id,),
        ).fetchall()

    print(
        f"Session {session['id']}: "
        f"{session['name']} "
        f"({session['session_type']})"
    )

    for target_pick in target_picks:
        drafted = []
        your_roster = []

        for row in rows:
            if row["overall_pick"] >= target_pick:
                break

            player = json.loads(
                row["player_json"]
            )

            drafted.append(
                {
                    "overall_pick": row["overall_pick"],
                    "round": row["round_number"],
                    "slot": row["slot"],
                    "player": player,
                }
            )

            if row["is_yours"]:
                your_roster.append(player)

        drafted_ids = {
            str(item["player"]["id"])
            for item in drafted
        }

        available = sorted(
            [
                player
                for player in players
                if str(player["id"]) not in drafted_ids
            ],
            key=lambda player: player["adp_rank"],
        )

        state = {
            "session_id": session_id,
            "session_type": session["session_type"],
            "session_name": session["name"],
            "season": session["season"],
            "teams": session["teams"],
            "your_slot": session["your_slot"],
            "current_pick": target_pick,
            "drafted": drafted,
            "your_roster": your_roster,
        }

        recommendations = get_recommendations(
            available,
            state,
        )

        print()
        print("=" * 78)
        print(f"PICK {target_pick}")

        print(
            "Roster:",
            ", ".join(
                f'{player["name"]} '
                f'({player["position"]})'
                for player in your_roster
            ) or "empty",
        )

        print()

        for index, item in enumerate(
            recommendations,
            start=1,
        ):
            player = item["player"]

            print(
                f'{index}. '
                f'{player["name"]:<26} '
                f'{player["position"]:<4} '
                f'score={item["score"]:<6} '
                f'{item["action"]}'
            )

            for reason in item["reasons"]:
                print(
                    f"     - {reason}"
                )


if __name__ == "__main__":
    main()
