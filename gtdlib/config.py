from gtdlib.store import ensure_config, normalize_context


def get_contexts(base_dir):

    cfg = ensure_config(base_dir)

    contexts = [normalize_context(c) for c in cfg.get("contexts", [])]

    return sorted(set(contexts))

