package com.beemer.service;

import com.beemer.math.IndianFormat;
import com.beemer.math.SeriesMath;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class SipService {
    private final PriceService prices;

    public SipService(PriceService prices) { this.prices = prices; }

    public Map<String, Object> simulate(String symbol, int startYear, double monthly) {
        List<SeriesMath.Pt> s = prices.adj(symbol);
        SeriesMath.Sip sip = SeriesMath.sip(s, monthly, LocalDate.of(startYear, 1, 1));
        if (sip == null) throw new IllegalArgumentException("No prices from " + startYear);
        List<SeriesMath.Pt> sub = s.stream().filter(p -> !p.date().isBefore(LocalDate.of(startYear, 1, 1))).toList();
        double lump = sip.invested() * sub.get(sub.size() - 1).value() / sub.get(0).value();
        double multiple = sip.value() / sip.invested();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("invested", IndianFormat.lakh(sip.invested()));
        out.put("investedExpl", sip.months() + " instalments since " + IndianFormat.monthYear(sip.start()) + ".");
        out.put("value", IndianFormat.lakh(sip.value()));
        out.put("valueExpl", IndianFormat.fixed(multiple, 2) + "× invested.");
        out.put("valueTone", sip.value() > sip.invested() ? "pos" : "neg");
        out.put("xirr", sip.xirr() == null ? "–" : IndianFormat.pct(sip.xirr()) + "/yr");
        out.put("xirrExpl", "Annual return, timing-weighted.");
        out.put("lump", IndianFormat.lakh(lump));
        out.put("lumpExpl", "Invested on day one. " + IndianFormat.pct(SeriesMath.cagr(sub, null)) + "/yr.");
        out.put("x", sip.valuePath().stream().map(p -> p.date().toString()).toList());
        out.put("val", sip.valuePath().stream().map(SeriesMath.Pt::value).toList());
        out.put("inv", sip.investedPath().stream().map(SeriesMath.Pt::value).toList());
        out.put("raw", Map.of("invested", sip.invested(), "value", sip.value(), "xirr", sip.xirr() == null ? 0 : sip.xirr(), "months", sip.months(), "lump", lump));
        return out;
    }
}
