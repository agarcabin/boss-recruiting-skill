"""Per-task goals: defaults are not global limits."""


def resolve(target=None,max_views=None):
    greetings=150 if target is None else target
    views=max(300,greetings) if max_views is None else max_views
    if type(greetings) is not int or greetings<1 or type(views) is not int or views<1:
        raise ValueError('target/max_views must be positive integers')
    return greetings,views
