BUSY_WORKING_ROSTER = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,
    "K": 1,
    "DEF": 1,
    "BN": 5,
    "IR": 1,
}

FLEX_ELIGIBLE = {
    "RB",
    "WR",
    "TE",
}

DRAFT_ROSTER_SIZE = (
    BUSY_WORKING_ROSTER["QB"]
    + BUSY_WORKING_ROSTER["RB"]
    + BUSY_WORKING_ROSTER["WR"]
    + BUSY_WORKING_ROSTER["TE"]
    + BUSY_WORKING_ROSTER["FLEX"]
    + BUSY_WORKING_ROSTER["K"]
    + BUSY_WORKING_ROSTER["DEF"]
    + BUSY_WORKING_ROSTER["BN"]
)

