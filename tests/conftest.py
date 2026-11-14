import os


# Leave log verbosity disabled by default; enable explicitly with
# PYTCHAT_VERBOSE_LOGS=1 or by passing verbose=True to pytchat.create().
os.environ.pop('PYTCHAT_VERBOSE_LOGS', None)
