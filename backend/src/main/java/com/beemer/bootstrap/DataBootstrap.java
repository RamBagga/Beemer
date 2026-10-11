package com.beemer.bootstrap;

import com.beemer.config.BeemerProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.sql.Connection;
import java.sql.DriverManager;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.GZIPInputStream;

/**
 * Mirror of bootstrap.py: download the data-latest release when market.db is missing or stale.
 * Local data with no manifest is never overwritten. Metrics parquet is imported into SQLite
 * so request handling only needs JDBC.
 */
public final class DataBootstrap {
    private static final Logger log = LoggerFactory.getLogger(DataBootstrap.class);
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String UA = "beemer-bootstrap/1.0";

    private final BeemerProperties props;
    private final HttpClient http = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).connectTimeout(Duration.ofSeconds(20)).build();

    public DataBootstrap(BeemerProperties props) {
        this.props = props;
    }

    /** @return true when a new snapshot was installed */
    public synchronized boolean ensure() {
        try {
            Files.createDirectories(props.dataDir());
            boolean have = valid(props.dbFile());
            JsonNode manifest = read(props.manifest());
            if (have && !stale(manifest)) {
                importMetricsIfNeeded();
                return false;
            }
            try {
                boolean updated = download();
                importMetricsIfNeeded();
                return updated;
            } catch (Exception e) {
                log.warn("could not download published data: {}", e.toString());
                if (!valid(props.dbFile()) && "full".equalsIgnoreCase(props.getBootstrapFallback())) {
                    runPipeline();
                    importMetricsIfNeeded();
                    return true;
                }
                importMetricsIfNeeded();
                return false;
            }
        } catch (Exception e) {
            log.warn("data bootstrap failed: {}", e.toString());
            return false;
        }
    }

    private void importMetricsIfNeeded() {
        if (!Files.exists(props.parquet()) || !valid(props.dbFile())) return;
        try {
            if (metricsRows() > 0) return;
            int n = new MetricsImporter().importParquet(props.dbFile(), props.parquet());
            log.info("imported {} company_metrics rows from parquet", n);
        } catch (Exception e) {
            log.warn("metrics import skipped: {}", e.toString());
        }
    }

    private int metricsRows() {
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + props.dbFile())) {
            try (var st = c.createStatement(); var rs = st.executeQuery("SELECT COUNT(*) FROM company_metrics")) {
                return rs.next() ? rs.getInt(1) : 0;
            }
        } catch (Exception e) {
            return 0;
        }
    }

    private boolean download() throws Exception {
        Map<String, String> urls = assetUrls();
        if (!urls.containsKey("manifest.json")) throw new IllegalStateException("no published data for " + props.getRepo() + "@" + props.getTag());
        Path tmp = Files.createTempDirectory(props.dataDir(), "dl-");
        try {
            Path man = tmp.resolve("manifest.json");
            fetch(urls.get("manifest.json"), man);
            JsonNode remote = read(man);
            JsonNode local = read(props.manifest());
            String remoteAt = remote == null ? null : text(remote, "generated_at");
            String localAt = local == null ? null : text(local, "generated_at");
            if (valid(props.dbFile()) && remoteAt != null && remoteAt.equals(localAt)) {
                touch(local, remoteAt);
                log.info("published data unchanged ({})", remoteAt);
                return false;
            }
            Path gz = tmp.resolve("market.db.gz");
            Path dbTmp = tmp.resolve("market.db");
            Path metTmp = tmp.resolve("metrics.parquet");
            fetch(urls.get("market.db.gz"), gz);
            try (InputStream in = new GZIPInputStream(Files.newInputStream(gz)); OutputStream out = Files.newOutputStream(dbTmp)) {
                in.transferTo(out);
            }
            fetch(urls.get("metrics.parquet"), metTmp);
            if (!valid(dbTmp) || Files.size(metTmp) == 0) throw new IllegalStateException("downloaded data failed validation");
            Files.move(dbTmp, props.dbFile(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            Files.move(metTmp, props.parquet(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            ObjectNode saved = remote == null ? JSON.createObjectNode() : (ObjectNode) remote;
            saved.put("checked_at", Instant.now().toString());
            JSON.writerWithDefaultPrettyPrinter().writeValue(props.manifest().toFile(), saved);
            log.info("installed published data generated at {}", remoteAt);
            return true;
        } finally {
            try (var walk = Files.walk(tmp)) {
                walk.sorted(java.util.Comparator.reverseOrder()).forEach(p -> { try { Files.deleteIfExists(p); } catch (Exception ignored) {} });
            }
        }
    }

    private Map<String, String> assetUrls() throws Exception {
        String base = props.getDataUrl() == null ? "" : props.getDataUrl().replaceAll("/$", "");
        String[] files = {"manifest.json", "market.db.gz", "metrics.parquet"};
        Map<String, String> out = new LinkedHashMap<>();
        if (!base.isBlank()) {
            for (String f : files) out.put(f, base + "/" + f);
            return out;
        }
        String token = props.getGithubToken() == null ? "" : props.getGithubToken();
        if (token.isBlank()) {
            for (String f : files) out.put(f, "https://github.com/" + props.getRepo() + "/releases/download/" + props.getTag() + "/" + f);
            return out;
        }
        HttpRequest req = HttpRequest.newBuilder(URI.create("https://api.github.com/repos/" + props.getRepo() + "/releases/tags/" + props.getTag()))
                .header("User-Agent", UA).header("Authorization", "Bearer " + token).header("Accept", "application/vnd.github+json")
                .timeout(Duration.ofSeconds(30)).GET().build();
        JsonNode body = JSON.readTree(http.send(req, HttpResponse.BodyHandlers.ofString()).body());
        Map<String, String> assets = new LinkedHashMap<>();
        for (JsonNode a : body.get("assets")) assets.put(a.get("name").asText(), a.get("url").asText());
        for (String f : files) if (assets.containsKey(f)) out.put(f, assets.get(f));
        return out;
    }

    private void fetch(String url, Path dest) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url)).header("User-Agent", UA).timeout(Duration.ofSeconds(120));
        if (props.getGithubToken() != null && !props.getGithubToken().isBlank() && url.contains("api.github.com")) {
            b.header("Authorization", "Bearer " + props.getGithubToken()).header("Accept", "application/octet-stream");
        }
        HttpResponse<InputStream> res = http.send(b.GET().build(), HttpResponse.BodyHandlers.ofInputStream());
        if (res.statusCode() >= 400) throw new IllegalStateException("GET " + url + " → " + res.statusCode());
        try (InputStream in = res.body()) {
            Files.copy(in, dest, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private void touch(JsonNode local, String generatedAt) throws Exception {
        ObjectNode n = local == null ? JSON.createObjectNode() : (ObjectNode) local;
        if (generatedAt != null) n.put("generated_at", generatedAt);
        n.put("checked_at", Instant.now().toString());
        JSON.writerWithDefaultPrettyPrinter().writeValue(props.manifest().toFile(), n);
    }

    static boolean valid(Path db) {
        if (!Files.exists(db)) return false;
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            try (var st = c.createStatement(); var rs = st.executeQuery("SELECT COUNT(*) FROM prices")) {
                return rs.next() && rs.getInt(1) > 0;
            }
        } catch (Exception e) {
            return false;
        }
    }

    private boolean stale(JsonNode manifest) {
        if (manifest == null || manifest.isNull()) return false;
        String stamp = text(manifest, "checked_at");
        if (stamp == null) stamp = text(manifest, "generated_at");
        if (stamp == null) return true;
        try {
            Instant last = Instant.parse(stamp);
            return Duration.between(last, Instant.now()).toSeconds() > props.getMaxAgeHours() * 3600;
        } catch (Exception e) {
            return true;
        }
    }

    private void runPipeline() throws Exception {
        Path script = props.dataDir().getParent().resolve("update_data.py");
        if (!Files.exists(script)) script = Path.of("update_data.py");
        log.info("building data with {}", script);
        Process p = new ProcessBuilder("python3", script.toString()).directory(script.getParent().toFile()).inheritIO().start();
        if (p.waitFor() != 0) throw new IllegalStateException("update_data.py failed");
    }

    private static JsonNode read(Path p) {
        try {
            if (!Files.exists(p)) return null;
            return JSON.readTree(p.toFile());
        } catch (Exception e) {
            return null;
        }
    }

    private static String text(JsonNode n, String k) {
        JsonNode v = n.get(k);
        return v == null || v.isNull() ? null : v.asText();
    }
}
