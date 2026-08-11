from mock_data import get_dashboard_data


def get_fantasy_data():
    """
    Temporary data provider.

    Once Yahoo Fantasy API access is approved, this function
    will retrieve live league, roster, player and draft data.
    """
    return get_dashboard_data()
