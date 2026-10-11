package com.beemer.web;

import com.beemer.api.NoDataException;
import com.beemer.api.NotFoundException;
import com.beemer.math.ScreenerFilter;
import com.beemer.service.CockpitService;
import com.beemer.service.CompanyService;
import com.beemer.service.PicksService;
import com.beemer.service.PriceService;
import com.beemer.service.ScreenerService;
import com.beemer.service.SipService;
import com.beemer.math.SeriesMath;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class ApiController {
    private final CockpitService cockpit;
    private final ScreenerService screener;
    private final CompanyService companies;
    private final PicksService picks;
    private final SipService sip;
    private final PriceService prices;

    public ApiController(CockpitService cockpit, ScreenerService screener, CompanyService companies,
                         PicksService picks, SipService sip, PriceService prices) {
        this.cockpit = cockpit;
        this.screener = screener;
        this.companies = companies;
        this.picks = picks;
        this.sip = sip;
        this.prices = prices;
    }

    @GetMapping("/api/cockpit")
    public Map<String, Object> cockpit() { return cockpit.view(); }

    @GetMapping("/api/screener")
    public Map<String, Object> screener(
            @RequestParam(required = false) List<String> subsector,
            @RequestParam(defaultValue = "0") int minScore,
            @RequestParam(defaultValue = "150") double maxPe,
            @RequestParam(defaultValue = "2") double maxDe,
            @RequestParam(defaultValue = "0") int minRoe,
            @RequestParam(defaultValue = "false") boolean profitable,
            @RequestParam(defaultValue = "false") boolean seasoned,
            @RequestParam(defaultValue = "false") boolean belowValue) {
        return screener.screen(new ScreenerFilter.Query(
                subsector == null ? List.of() : subsector, minScore, maxPe, maxDe, minRoe, profitable, seasoned, belowValue));
    }

    @GetMapping("/api/companies")
    public List<Map<String, Object>> companies() { return companies.list(); }

    @GetMapping("/api/companies/{symbol}")
    public Map<String, Object> company(@PathVariable String symbol) { return companies.company(symbol.toUpperCase()); }

    @GetMapping("/api/picks")
    public Map<String, Object> picks() { return picks.view(); }

    @GetMapping("/api/academy")
    public Map<String, Object> academy() {
        Map<String, Object> p = picks.view();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("trackRecord", p.get("trackRecord"));
        out.put("backtest", p.get("backtest"));
        return out;
    }

    @GetMapping("/api/indices")
    public List<Map<String, Object>> indices() {
        List<Map<String, Object>> out = new java.util.ArrayList<>();
        for (var e : Map.of("Nifty IT", "^CNXIT", "Nifty 50", "^NSEI", "Sensex", "^BSESN").entrySet()) {
            List<SeriesMath.Pt> s = prices.adj(e.getValue());
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("name", e.getKey());
            row.put("symbol", e.getValue());
            row.put("first", s.get(0).date().toString());
            row.put("last", s.get(s.size() - 1).date().toString());
            row.put("cagr", SeriesMath.cagr(s, null));
            out.add(row);
        }
        return out;
    }

    @PostMapping("/api/sip-simulator")
    public Map<String, Object> sip(@RequestBody SipRequest body) {
        return sip.simulate(body.symbol(), body.startYear(), body.monthly() <= 0 ? 10000 : body.monthly());
    }

    public record SipRequest(String symbol, int startYear, double monthly) {}
}

@RestControllerAdvice
class ApiErrors {
    @ExceptionHandler(NoDataException.class)
    ResponseEntity<Map<String, String>> noData(NoDataException e) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(Map.of("error", e.getMessage()));
    }

    @ExceptionHandler(NotFoundException.class)
    ResponseEntity<Map<String, String>> missing(NotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", e.getMessage()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<Map<String, String>> bad(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
    }
}
