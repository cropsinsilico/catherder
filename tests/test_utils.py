import classes


def test_milestone2issue():
    r"""Test conversion from a milestone to an issue and then back to ensure
    the original milestone will be returned."""
    fname_smartsheet = "./Crops in silico Project Goals.csv"
    x_sm = classes.SmartsheetAPI()
    x_gh = classes.GithubAPI()
    milestones = x_sm.load_local(fname_smartsheet)['milestones']
    for milestone0 in milestones:
        issue = x_gh.get_issue_from_Smartsheet_milestone(milestone0)
        milestone1 = x_sm.get_milestone_from_Github_issue(issue)
        if milestone1['Status'].startswith('In Progress'):
            milestone1['Status'] = 'In Progress'
        assert(milestone0 == milestone1)
