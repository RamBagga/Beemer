package com.beemer.web;

import com.beemer.service.DatasetsService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class DatasetsController {
    private final DatasetsService datasets;

    public DatasetsController(DatasetsService datasets) { this.datasets = datasets; }

    /** Ownership, dividends, corporate actions, board meetings, insider trades, deals, official results, delivery. */
    @GetMapping("/api/companies/{symbol}/filings")
    public Map<String, Object> filings(@PathVariable String symbol) { return datasets.filings(symbol.toUpperCase()); }

    /** NSE index valuations: latest P/E, P/B, yield and 10-year median P/E. */
    @GetMapping("/api/market")
    public Map<String, Object> market() { return datasets.market(); }

    /** Row counts per dataset and the latest run of each source. */
    @GetMapping("/api/data/inventory")
    public Map<String, Object> inventory() { return datasets.inventory(); }
}
