import re

from omni_analyst.types import ResearchState


def _company_from_text(text: str) -> str:
    tag_match = re.search(r"\[COMPANY:(NVIDIA|AMD|INTEL|UNKNOWN)\]", text)
    if tag_match:
        return tag_match.group(1)
    lowered = text.lower()
    if "nvidia" in lowered:
        return "NVIDIA"
    if "advanced micro devices" in lowered or "amd" in lowered:
        return "AMD"
    if "intel" in lowered or "intc" in lowered:
        return "INTEL"
    return ""


def _normalize_number(value: str, unit: str | None) -> str:
    number = value.replace(",", "").strip()
    if not unit:
        return number
    unit = unit.lower()
    if unit in ("b", "bn", "billion"):
        return f"{number}B"
    if unit in ("m", "mm", "million"):
        return f"{number}M"
    return number


def _extract_metric(text: str, patterns: list[str], is_percent: bool = False) -> str:
    value, _ = _find_metric(text, patterns, is_percent)
    return value


def _find_metric(
    text: str, patterns: list[str], is_percent: bool = False
) -> tuple[str, int]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            unit = match.group(2).strip() if match.lastindex and match.lastindex >= 2 else None
            value = _normalize_number(value, unit)
            if is_percent:
                return f"{value}%", match.start()
            return f"${value}", match.start()
    return "N/A", -1


def _latest_period(text: str) -> tuple[str, int]:
    matches = []
    for match in re.finditer(r"Q(\d)\s*FY(\d{2})", text, re.IGNORECASE):
        q = int(match.group(1))
        fy = int(match.group(2))
        matches.append((fy, q, match.start(), match.group(0)))
    if not matches:
        return "N/A", -1
    fy, q, idx, raw = sorted(matches, reverse=True)[0]
    return raw.replace(" ", ""), idx


def _latest_fy(text: str) -> int | None:
    years = []
    for match in re.finditer(r"FY(\d{2})", text, re.IGNORECASE):
        years.append(int(match.group(1)))
    return max(years) if years else None


def _block_for_fy(text: str, fy: int) -> tuple[str, str]:
    lines = text.splitlines()
    fy_tag = f"FY{fy:02d}"
    for i, line in enumerate(lines):
        if fy_tag in line:
            matches = re.findall(r"(Q\d\s*FY\d{2})", line, re.IGNORECASE)
            if len(matches) < 2:
                continue
            period = matches[0].replace(" ", "") if matches else "N/A"
            block = "\n".join(lines[i : i + 10])
            return block, period
    return "", "N/A"


def _extract_period(text: str) -> str:
    period, _ = _latest_period(text)
    if period != "N/A":
        return period
    match = re.search(r"(Q\d\s*(?:20)?\d{2,4})", text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")
    return "N/A"


def _nearest_period(text: str, index: int) -> str:
    if index < 0:
        return "N/A"
    window = text[max(0, index - 300) : index]
    for line in reversed(window.splitlines()):
        matches = re.findall(r"(Q\d\s*FY\d{2})", line, re.IGNORECASE)
        if matches:
            return matches[0].replace(" ", "")
    matches = []
    for match in re.finditer(r"(Q\d\s*FY\d{2})", text, re.IGNORECASE):
        if match.start() <= index:
            matches.append(match.group(1).replace(" ", ""))
    return matches[-1] if matches else "N/A"


def _clean_extracted_text(text: str) -> str:
    if not text:
        return text
    cleaned = text.replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"(?:(?<=\b)[A-Za-z])(?:\s+(?=[A-Za-z]\b))+", "", cleaned)
    cleaned = re.sub(r",(?=\S)", ", ", cleaned)
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    return cleaned.strip()


def _metric_source(
    value: str, table_text: str, full_text: str, patterns: list[str]
) -> tuple[str, str]:
    if value == "N/A":
        return "none", "low"
    if table_text and any(re.search(p, table_text, re.IGNORECASE) for p in patterns):
        return "pdf", "high"
    if full_text and any(re.search(p, full_text, re.IGNORECASE) for p in patterns):
        return "web", "medium"
    return "unknown", "low"


def build_comparison_table(state: ResearchState) -> str:
    buckets: dict[str, list[str]] = {"NVIDIA": [], "AMD": [], "INTEL": []}
    for doc in state.get("documents", []):
        company = _company_from_text(doc)
        if company and company in buckets:
            buckets[company].append(doc)

    rows = []
    for company in ("NVIDIA", "AMD", "INTEL"):
        text = "\n".join(buckets[company])
        table_text = "\n".join(
            line
            for line in state.get("extracted_tables", [])
            if f"[COMPANY:{company}]" in line
        )
        table_text = _clean_extracted_text(table_text)
        period, idx = _latest_period(text)
        target_text = text
        if idx >= 0:
            target_text = text[max(0, idx - 200) : idx + 2000]
        period = period if period != "N/A" else _extract_period(text)
        revenue_patterns = [
            r"(?:Total\s+)?Revenue\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Net\s+revenue\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Sales\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
        ]
        margin_patterns = [
            r"Gross margin\s*([0-9]+(?:\.[0-9]+)?)%",
            r"Gross margin\s*([0-9]+(?:\.[0-9]+)?)\s*percent",
        ]
        op_income_patterns = [
            r"Operating income\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Operating profit\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
        ]
        net_income_patterns = [
            r"Net income\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Net income attributable to .*?\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Net earnings\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
        ]
        eps_patterns = [
            r"Diluted earnings per share\*?\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Diluted EPS\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"Earnings per share\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
            r"EPS\s*\$?\s*([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
        ]

        revenue, revenue_idx = _find_metric(target_text, revenue_patterns)
        gross_margin = _extract_metric(target_text, margin_patterns, is_percent=True)
        operating_income = _extract_metric(target_text, op_income_patterns)
        net_income = _extract_metric(target_text, net_income_patterns)
        eps = _extract_metric(target_text, eps_patterns)

        latest_fy = _latest_fy(text)
        if latest_fy is not None:
            block, block_period = _block_for_fy(text, latest_fy)
            if block:
                block_revenue = _extract_metric(block, revenue_patterns)
                if block_revenue != "N/A":
                    revenue = block_revenue
                    gross_margin = _extract_metric(block, margin_patterns, is_percent=True)
                    operating_income = _extract_metric(block, op_income_patterns)
                    net_income = _extract_metric(block, net_income_patterns)
                    eps = _extract_metric(block, eps_patterns)
                    if block_period != "N/A":
                        period = block_period

        if revenue == "N/A":
            revenue, revenue_idx = _find_metric(text, revenue_patterns)
        revenue_source_patterns = list(revenue_patterns)
        margin_source_patterns = list(margin_patterns)
        op_source_patterns = list(op_income_patterns)
        net_source_patterns = list(net_income_patterns)
        eps_source_patterns = list(eps_patterns)
        if company == "INTEL":
            intel_eps_patterns = [
                r"Earnings \(loss\) per share[^\n]*?\$\(?([0-9][0-9,\.]+)\)?",
                r"EPS[^\n]*?\$\(?([0-9][0-9,\.]+)\)?",
            ]
            full_year_revenue = re.search(
                r"Full[-\s]year revenue was\s*\$?([0-9][0-9,\.]+)\s*billion",
                text,
                re.IGNORECASE,
            )
            revenue_b = re.search(
                r"Revenue\s*\([^)]*B\)\s*\$?([0-9][0-9,\.]+)",
                text,
                re.IGNORECASE,
            )
            if full_year_revenue:
                revenue = f"${_normalize_number(full_year_revenue.group(1), 'b')}"
                revenue_idx = full_year_revenue.start()
            elif revenue_b:
                revenue = f"${_normalize_number(revenue_b.group(1), 'b')}"
                revenue_idx = revenue_b.start()
            revenue_source_patterns.extend(
                [
                    r"Full[-\s]year revenue was\s*\$?([0-9][0-9,\.]+)\s*billion",
                    r"Revenue\s*\([^)]*B\)\s*\$?([0-9][0-9,\.]+)",
                ]
            )
            if gross_margin == "N/A":
                gross_margin = _extract_metric(text, margin_patterns, is_percent=True)
            if operating_income == "N/A":
                operating_b = re.search(
                    r"Operating income \(loss\)\s*\(\$B\)\s*\$?\(?([0-9][0-9,\.]+)\)?",
                    text,
                    re.IGNORECASE,
                )
                if operating_b:
                    value = operating_b.group(1).strip()
                    normalized = _normalize_number(value, "b")
                    is_negative = bool(
                        re.search(r"\(\s*\$?\(?%s\)?\s*\)" % re.escape(value), operating_b.group(0))
                    ) or "-" in operating_b.group(0)
                    operating_income = f"${normalized}"
                    if is_negative:
                        operating_income = f"-${normalized}"
                else:
                    intel_operating_patterns = [
                        r"Operating income \(loss\)[\s\S]{0,80}?\$?\(?([0-9][0-9,\.]+)\)?",
                        r"Operating income \(loss\)\s*\(\$?([0-9][0-9,\.]+)\)",
                        r"Operating income\s*\$?([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
                    ]
                    for pattern in intel_operating_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if not match:
                            continue
                        value = match.group(1).strip()
                        unit = match.group(2).strip() if match.lastindex and match.lastindex >= 2 else None
                        normalized = _normalize_number(value, unit)
                        is_negative = bool(
                            re.search(r"\(\s*\$?\(?%s\)?\s*\)" % re.escape(value), match.group(0))
                        ) or "-" in match.group(0)
                        operating_income = f"${normalized}"
                        if is_negative:
                            operating_income = f"-${normalized}"
                        break
            if (
                operating_income != "N/A"
                and "M" not in operating_income
                and "B" not in operating_income
                and isinstance(revenue, str)
                and revenue.endswith("B")
            ):
                raw_value = operating_income.replace("$", "").replace("-", "")
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_value):
                    if float(raw_value) < 1000:
                        sign = "-" if operating_income.startswith("-") else ""
                        operating_income = f"{sign}${raw_value}M"
            if net_income == "N/A":
                intel_net_income_patterns = [
                    r"Net income \(loss\)[\s\S]{0,80}?\$\(?([0-9][0-9,\.]+)\)?",
                    r"Net income \(loss\)[\s\S]{0,80}?\(\$?([0-9][0-9,\.]+)\)",
                    r"Net income \(loss\)[\s\S]{0,80}?\(\$B\)\s*\$?\(?([0-9][0-9,\.]+)\)?",
                ]
                for pattern in intel_net_income_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        unit = "b" if "($B)" in match.group(0) else None
                        normalized = _normalize_number(value, unit)
                        is_negative = bool(
                            re.search(r"\(\s*\$?\(?%s\)?\s*\)" % re.escape(value), match.group(0))
                        ) or "-" in match.group(0)
                        net_income = f"${normalized}"
                        if is_negative:
                            net_income = f"-${normalized}"
                        break
                if net_income == "N/A":
                    net_income = _extract_metric(text, net_income_patterns)
            if (
                net_income != "N/A"
                and "M" not in net_income
                and "B" not in net_income
                and isinstance(revenue, str)
                and revenue.endswith("B")
            ):
                raw_value = net_income.replace("$", "").replace("-", "")
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_value):
                    if float(raw_value) < 1000:
                        sign = "-" if net_income.startswith("-") else ""
                        net_income = f"{sign}${raw_value}M"
            if eps == "N/A":
                eps = _extract_metric(text, intel_eps_patterns)
            eps_source_patterns.extend(intel_eps_patterns)
            if period == "N/A":
                full_year = re.search(r"Full[-\s]Year\s*20(\d{2})", text, re.IGNORECASE)
                if full_year:
                    period = f"FY20{full_year.group(1)}"
                else:
                    q4_year = re.search(r"Fourth[-\s]Quarter\s*20(\d{2})", text, re.IGNORECASE)
                    if q4_year:
                        period = f"Q4 20{q4_year.group(1)}"
        if company == "AMD":
            amd_period = re.search(
                r"(first|second|third|fourth)\s+quarter\s+(?:of\s+)?20(\d{2})",
                text,
                re.IGNORECASE,
            )
            if period == "N/A" and amd_period:
                quarter_map = {
                    "first": "Q1",
                    "second": "Q2",
                    "third": "Q3",
                    "fourth": "Q4",
                }
                period = f"{quarter_map.get(amd_period.group(1).lower(), 'Q?')} 20{amd_period.group(2)}"
            if period == "N/A":
                q_period = re.search(r"Q([1-4])\s*20(\d{2})", text, re.IGNORECASE)
                if q_period:
                    period = f"Q{q_period.group(1)} 20{q_period.group(2)}"

            amd_operating_patterns = [
                r"Operating income\s*\$?([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
                r"Operating income \(loss\)[\s\S]{0,80}?\$?\(?([0-9][0-9,\.]+)\)?",
                r"Operating loss[\s\S]{0,80}?\$?\(?([0-9][0-9,\.]+)\)?",
                r"operating (?:income|loss) (?:was|of)\s*\$?\(?([0-9][0-9,\.]+)\)?",
            ]
            amd_net_patterns = [
                r"Net income\s*\$?([0-9][0-9,\.]+)\s*(b|bn|billion|m|mm|million)?",
                r"Net income \(loss\)[\s\S]{0,80}?\$?\(?([0-9][0-9,\.]+)\)?",
                r"Net loss[\s\S]{0,80}?\$?\(?([0-9][0-9,\.]+)\)?",
                r"Net income \(loss\) attributable to .*?[\s\S]{0,80}?\$?\(?([0-9][0-9,\.]+)\)?",
                r"net income (?:was|of)\s*\$?\(?([0-9][0-9,\.]+)\)?",
            ]
            amd_eps_patterns = [
                r"Diluted (?:earnings|loss) per share[^\n]*?\$?\(?([0-9][0-9,\.]+)\)?",
                r"Non-GAAP diluted (?:earnings|loss) per share[^\n]*?\$?\(?([0-9][0-9,\.]+)\)?",
                r"Diluted (?:earnings per share|EPS)[^\n]*?\$?\(?([0-9][0-9,\.]+)\)?",
                r"EPS[^\n]*?\$?\(?([0-9][0-9,\.]+)\)?",
                r"Earnings from continuing operations[^\n]*?\$?\s*([0-9][0-9,\.]+)",
            ]
            op_source_patterns.extend(amd_operating_patterns)
            net_source_patterns.extend(amd_net_patterns)
            eps_source_patterns.extend(amd_eps_patterns)

            if operating_income == "N/A":
                operating_income, _ = _find_metric(text, amd_operating_patterns)
            for pattern in amd_operating_patterns[1:]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    normalized = _normalize_number(value, None)
                    is_negative = "loss" in match.group(0).lower() or "(" in match.group(0)
                    operating_income = f"${normalized}"
                    if is_negative:
                        operating_income = f"-${normalized}"
                    break
            if net_income == "N/A":
                net_income, _ = _find_metric(text, amd_net_patterns)
            for pattern in amd_net_patterns[1:]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    normalized = _normalize_number(value, None)
                    is_negative = "loss" in match.group(0).lower() or "(" in match.group(0)
                    net_income = f"${normalized}"
                    if is_negative:
                        net_income = f"-${normalized}"
                    break
            if eps == "N/A":
                eps, _ = _find_metric(text, amd_eps_patterns)
                if eps == "N/A":
                    for pattern in amd_eps_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            value = match.group(1).strip()
                            normalized = _normalize_number(value, None)
                            is_negative = "loss" in match.group(0).lower() or "(" in match.group(0)
                            eps = f"${normalized}"
                            if is_negative:
                                eps = f"-${normalized}"
                            break
            if (
                isinstance(operating_income, str)
                and operating_income != "N/A"
                and "M" not in operating_income
                and "B" not in operating_income
                and isinstance(revenue, str)
                and revenue.endswith("B")
            ):
                raw_value = operating_income.replace("$", "").replace("-", "")
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_value):
                    sign = "-" if operating_income.startswith("-") else ""
                    operating_income = f"{sign}${raw_value}M"
            if (
                isinstance(net_income, str)
                and net_income != "N/A"
                and "M" not in net_income
                and "B" not in net_income
                and isinstance(revenue, str)
                and revenue.endswith("B")
            ):
                raw_value = net_income.replace("$", "").replace("-", "")
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_value):
                    sign = "-" if net_income.startswith("-") else ""
                    net_income = f"{sign}${raw_value}M"
        if revenue_idx >= 0:
            nearest = _nearest_period(text, revenue_idx)
            if nearest != "N/A":
                period = nearest
        if gross_margin == "N/A":
            gross_margin = _extract_metric(text, margin_patterns, is_percent=True)
        if operating_income == "N/A":
            operating_income = _extract_metric(text, op_income_patterns)
        if net_income == "N/A":
            net_income = _extract_metric(text, net_income_patterns)
        if eps == "N/A":
            eps = _extract_metric(text, eps_patterns)
        rev_src, rev_conf = _metric_source(
            revenue, table_text, text, revenue_source_patterns
        )
        mar_src, mar_conf = _metric_source(
            gross_margin, table_text, text, margin_source_patterns
        )
        op_src, op_conf = _metric_source(
            operating_income, table_text, text, op_source_patterns
        )
        net_src, net_conf = _metric_source(
            net_income, table_text, text, net_source_patterns
        )
        eps_src, eps_conf = _metric_source(eps, table_text, text, eps_source_patterns)
        rows.append(
            f"| {company} | {period} | {revenue} | {rev_src}/{rev_conf} | "
            f"{gross_margin} | {mar_src}/{mar_conf} | {operating_income} | "
            f"{op_src}/{op_conf} | {net_income} | {net_src}/{net_conf} | "
            f"{eps} | {eps_src}/{eps_conf} |"
        )

    header = (
        "| Sirket | Donem | Gelir | Gelir Kaynak/Guven | Brut Marj | "
        "Brut Marj Kaynak/Guven | Faaliyet Geliri | Faaliyet Geliri Kaynak/Guven | "
        "Net Kar | Net Kar Kaynak/Guven | EPS | EPS Kaynak/Guven |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    return header + "\n" + "\n".join(rows)


def draft_report(state: ResearchState) -> ResearchState:
    sources = "\n".join(
        f"- {item.get('title', 'Kaynak')}: {item.get('url', '')}"
        for item in state["sources"]
    )
    comparison_table = build_comparison_table(state)
    tables_raw = "\n".join(state["extracted_tables"])
    tables = _clean_extracted_text(tables_raw) or "Gorsel veri yok."
    graph = "\n".join(state["graph_updates"]) or "GraphRAG guncellemesi yok."
    warnings = "\n".join(state.get("warnings", [])) or ""
    state["draft_report"] = (
        f"Soru: {state['question']}\n\n"
        f"Plan:\n" + "\n".join(f"- {step}" for step in state["plan"]) + "\n\n"
        f"Karsilastirma Tablosu:\n{comparison_table}\n\n"
        f"Grafik/Tablo Analizi:\n{tables}\n\n"
        f"GraphRAG:\n{graph}\n\n"
        f"Kaynaklar:\n{sources}"
    )
    if warnings:
        state["draft_report"] += f"\n\nUyarilar:\n{warnings}"
    return state


def finalize_report(state: ResearchState) -> ResearchState:
    state["final_report"] = (
        state["draft_report"] + "\n\n" + f"Critic Notu: {state['critique']}"
    )
    return state
