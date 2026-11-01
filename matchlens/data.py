from data_pipeline.espn.matches import load_matches


def finished(df):
    return df[df["regular"] & df["home_goals"].notna()].copy()


def upcoming(df):
    return df[df["state"].eq("pre")].copy()


__all__ = ["load_matches", "finished", "upcoming"]
