package com.beemer.web;

import com.beemer.data.MarketRepository;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class DataHealth implements HealthIndicator {
    private final MarketRepository repo;

    public DataHealth(MarketRepository repo) { this.repo = repo; }

    @Override
    public Health health() {
        if (!repo.ready()) return Health.down().withDetail("reason", "market data missing").build();
        return Health.up().withDetail("companies", repo.metrics().size()).build();
    }
}
