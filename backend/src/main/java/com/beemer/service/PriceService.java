package com.beemer.service;

import com.beemer.data.MarketRepository;
import com.beemer.math.PriceCleaner;
import com.beemer.math.SeriesMath;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class PriceService {
    private final MarketRepository repo;
    private volatile Map<LocalDate, Double> market;

    public PriceService(MarketRepository repo) { this.repo = repo; }

    @Cacheable(value = "prices", key = "#symbol")
    public List<SeriesMath.Pt> adj(String symbol) {
        return bars(symbol).stream().map(b -> new SeriesMath.Pt(b.date(), b.adj())).toList();
    }

    @Cacheable(value = "prices", key = "'c:' + #symbol")
    public List<SeriesMath.Pt> close(String symbol) {
        return bars(symbol).stream().map(b -> new SeriesMath.Pt(b.date(), b.close())).toList();
    }

    private List<PriceCleaner.Bar> bars(String symbol) {
        List<PriceCleaner.Bar> raw = repo.prices(symbol);
        if (symbol.startsWith("^")) {
            List<PriceCleaner.Bar> out = new ArrayList<>();
            for (PriceCleaner.Bar b : raw) if (b.close() > 0 && b.adj() > 0) out.add(b);
            return out;
        }
        return PriceCleaner.clean(raw, market()).bars();
    }

    private Map<LocalDate, Double> market() {
        Map<LocalDate, Double> cached = market;
        if (cached != null) return cached;
        synchronized (this) {
            if (market != null) return market;
            Map<LocalDate, Double> out = new HashMap<>();
            Double prev = null;
            for (PriceCleaner.Bar b : repo.prices("^BSESN")) {
                if (b.close() <= 0 || b.adj() <= 0) continue;
                if (prev != null && prev != 0) out.put(b.date(), b.adj() / prev - 1);
                prev = b.adj();
            }
            market = out;
            return out;
        }
    }
}
