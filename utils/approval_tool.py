from config import APPROVAL_RULES

def generate_approval_threshold_description():
    sorted_rules = sorted(APPROVAL_RULES.items(), key=lambda item: item[1])
    lines = []
    last_threshold = 0.0
    for i, (role, limit) in enumerate(sorted_rules):
        if limit == float("inf"):
            lines.append(f"{i+1} = Genehmigung durch {role.capitalize()} (ab {int(last_threshold) + 1} €)")
        else:
            lines.append(f"{i+1} = Genehmigung durch {role.capitalize()} (bis {int(limit)} €)")
            last_threshold = limit
    lines.insert(0, "0 = Genehmigung verweigern")
    return "\n".join(lines)
