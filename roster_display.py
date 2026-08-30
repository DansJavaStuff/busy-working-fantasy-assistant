from league_config import (
    BUSY_WORKING_ROSTER,
    FLEX_ELIGIBLE,
    normalised_position,
)


def build_roster_slots(roster):
    """
    Build a display-only Yahoo-style roster board.

    Players are assigned to their normal starting position
    first. Extra RB/WR/TE players fill FLEX, then all remaining
    players fill the bench in draft order.

    This does not affect draft/recommendation logic.
    """

    remaining = list(roster)

    slots = []


    def take_position(position):
        for index, player in enumerate(remaining):

            player_position = normalised_position(
                player.get("position")
            )

            if player_position == position:
                return remaining.pop(index)

        return None


    def take_flex():
        for index, player in enumerate(remaining):

            player_position = normalised_position(
                player.get("position")
            )

            if player_position in FLEX_ELIGIBLE:
                return remaining.pop(index)

        return None


    # Normal starting positions.
    for _ in range(BUSY_WORKING_ROSTER["QB"]):
        slots.append({
            "slot": "QB",
            "player": take_position("QB"),
        })

    for _ in range(BUSY_WORKING_ROSTER["RB"]):
        slots.append({
            "slot": "RB",
            "player": take_position("RB"),
        })

    for _ in range(BUSY_WORKING_ROSTER["WR"]):
        slots.append({
            "slot": "WR",
            "player": take_position("WR"),
        })

    for _ in range(BUSY_WORKING_ROSTER["TE"]):
        slots.append({
            "slot": "TE",
            "player": take_position("TE"),
        })

    for _ in range(BUSY_WORKING_ROSTER["FLEX"]):
        slots.append({
            "slot": "FLEX",
            "player": take_flex(),
        })

    for _ in range(BUSY_WORKING_ROSTER["K"]):
        slots.append({
            "slot": "K",
            "player": take_position("K"),
        })

    for _ in range(BUSY_WORKING_ROSTER["DEF"]):
        slots.append({
            "slot": "DST",
            "player": take_position("DST"),
        })

    # Anything not needed in a starting slot becomes bench.
    for _ in range(BUSY_WORKING_ROSTER["BN"]):
        player = (
            remaining.pop(0)
            if remaining
            else None
        )

        slots.append({
            "slot": "BN",
            "player": player,
        })

    return slots


if __name__ == "__main__":
    print(
        build_roster_slots([])
    )
