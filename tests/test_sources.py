"""Offline tests for the NSE source parsers (no network)."""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources import nse_archives, nse_corp, store  # noqa: E402


def test_iso_dates():
    assert store.iso("10-Jun-2026") == "2026-06-10"
    assert store.iso("30-JUN-2026") == "2026-06-30"
    assert store.iso("09-10-2026") == "2026-10-09"
    assert store.iso("-") is None


def test_classify_dividends_and_actions():
    assert nse_corp.classify_action("Interim Dividend - Rs 15 Per Share") == ("dividend", 15.0, None)
    k, amt, _ = nse_corp.classify_action("Annual General Meeting / Dividend - Final Rs 22 + Special Rs 10")
    assert k == "dividend" and amt == 32.0
    assert nse_corp.classify_action("Agm/ Dividend-130%", face_value=5)[1] == 6.5
    assert nse_corp.classify_action("Bonus 1:1") == ("bonus", None, "1:1")
    k, _, ratio = nse_corp.classify_action("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share")
    assert k == "split" and ratio == "10:2"
    assert nse_corp.classify_action("Buy Back")[0] == "buyback"


SHP = """<xbrli:xbrl>
<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI" unitRef="pure">0.1382</in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares>
<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="PublicShareholding_ContextI" unitRef="pure">0.8597</in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares>
<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="InstitutionsForeign_ContextI" unitRef="pure">0.2709</in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares>
<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="MutualFundsOrUTI_ContextI" unitRef="pure">0.23</in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares>
<in-bse-shp:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged contextRef="MainI">false</in-bse-shp:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged>
</xbrli:xbrl>"""


def test_shareholding_xbrl():
    out = nse_corp.parse_shp_xbrl(SHP)
    assert out["promoter"] == 13.82 and out["fii"] == 27.09 and out["mf"] == 23.0
    assert out["pledge_flag"] == "false"


RES_XML = """<xbrli:xbrl>
<in-bse-fin:RevenueFromOperations contextRef="OneD" unitRef="INR" decimals="-5">349150000000.00</in-bse-fin:RevenueFromOperations>
<in-bse-fin:RevenueFromOperations contextRef="FourD" unitRef="INR" decimals="-5">1024550000000.00</in-bse-fin:RevenueFromOperations>
<in-bse-fin:ProfitLossForPeriod contextRef="OneD" unitRef="INR" decimals="-5">63580000000.00</in-bse-fin:ProfitLossForPeriod>
<in-bse-fin:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations contextRef="OneD" unitRef="INRPerShare" decimals="2">15.35</in-bse-fin:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations>
</xbrli:xbrl>"""


def test_results_xml_in_crore():
    out = nse_corp.parse_results_xml(RES_XML)
    assert out["revenue"] == 34915.0 and out["net_profit"] == 6358.0 and out["eps"] == 15.35


RES_HTML = """<html><body><table>
<tr><th>Level of rounding used in financial results</th><td>Lakhs</td></tr>
<tr><th>Date of end of reporting period</th><td>30-06-2026</td><td>30-06-2026</td></tr>
<tr><th></th><th>Revenue from operations</th><td>39,95,700.00</td><td>39,95,700.00</td></tr>
<tr><th></th><th>Deferred tax</th><td>(12,900.00)</td></tr>
<tr><th></th><th>Total profit (loss) for period</th><td>7,24,900.00</td></tr>
<tr><th></th><th>Basic earnings (loss) per share from continuing and discontinued operations</th><td>17.87</td></tr>
</table></body></html>"""


def test_results_integrated_filing_html():
    out = nse_corp.parse_results_html(RES_HTML)
    assert out["revenue"] == 39957.0 and out["net_profit"] == 7249.0 and out["eps"] == 17.87
    assert out["_period_end"] == "2026-06-30"


def test_archive_parsers():
    body = (b"SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, "
            b"TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
            b"INFY, EQ, 09-Oct-2026, 997.00, 1007.30, 1030.90, 1007.30, 1023.00, 1023.40, 1022.02, 14094234, 144046.48, 205741, 7171148, 50.88\n"
            b"ABC, EQ, 09-Oct-2026, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1\n")
    rows = nse_archives._parse_delivery(body, {"INFY"})
    assert len(rows) == 1 and rows[0][1] == "2026-10-09" and rows[0][-1] == 50.88
    idx = (b"Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,"
           b"Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n"
           b"Nifty IT,09-10-2026,27905.85,28776.75,27901.85,28574.9,838.3,3.02,59070399,6445.42,17.97,5,3.96\n")
    r = nse_archives._parse_index(idx)[0]
    assert r[0] == "Nifty IT" and r[1] == "2026-10-09" and r[5] == 28574.9 and r[9] == 17.97


def test_schema_and_enrich(tmp_path):
    import json
    import expand_data
    con = sqlite3.connect(tmp_path / "t.db")
    store.ensure(con)
    con.execute("CREATE TABLE company_metrics(symbol TEXT PRIMARY KEY, name TEXT, subsector TEXT, theme TEXT, industry TEXT,"
                " buffett_score REAL, score_label TEXT, payload TEXT)")
    con.execute("INSERT INTO company_metrics VALUES ('INFY','Infosys','IT services','','',70,'Good',?)",
                (json.dumps({"symbol": "INFY", "price": 1000}),))
    con.execute("INSERT INTO shareholding(symbol, period, promoter, fii, dii, mf, public) VALUES ('INFY','2026-06-30',13.8,27.1,43.0,23.0,86.0)")
    con.execute("INSERT INTO corp_actions VALUES ('INFY', date('now','-30 days'), NULL, 'Dividend - Rs 25 Per Share', 'dividend', 25, NULL, 5, 'EQ')")
    con.commit()
    assert expand_data.enrich(con) == 1
    p = json.loads(con.execute("SELECT payload FROM company_metrics").fetchone()[0])
    assert p["own_promoter"] == 13.8 and p["div_ttm"] == 25 and p["div_yield_nse"] == 0.025
