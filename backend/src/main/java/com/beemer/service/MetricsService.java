package com.beemer.service;

import com.beemer.api.NoDataException;
import com.beemer.data.MarketRepository;
import com.beemer.data.Metric;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MetricsService {
    private final MarketRepository repo;

    public MetricsService(MarketRepository repo) { this.repo = repo; }

    @Cacheable("metrics")
    public List<Metric> all() {
        if (!repo.ready()) throw new NoDataException();
        List<Metric> rows = repo.metrics();
        if (rows.isEmpty()) throw new NoDataException();
        return rows;
    }
}
