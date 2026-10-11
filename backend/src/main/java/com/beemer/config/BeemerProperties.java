package com.beemer.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.nio.file.Path;

@ConfigurationProperties(prefix = "beemer")
public class BeemerProperties {
    private String dataDir = "../data";
    private String repo = "RamBagga/Beemer";
    private String tag = "data-latest";
    private String dataUrl = "";
    private double maxAgeHours = 6;
    private boolean bootstrapEnabled = true;
    private String bootstrapFallback = "none";
    private String githubToken = "";
    private String corsOrigins = "http://localhost:*,http://127.0.0.1:*";

    public Path dataDir() {
        Path p = Path.of(dataDir);
        if (!p.isAbsolute()) p = Path.of(System.getProperty("user.dir")).resolve(p).normalize();
        return p;
    }

    public Path dbFile() { return dataDir().resolve("market.db"); }
    public Path parquet() { return dataDir().resolve("metrics.parquet"); }
    public Path manifest() { return dataDir().resolve(".published_manifest.json"); }

    public String getDataDir() { return dataDir; }
    public void setDataDir(String dataDir) { this.dataDir = dataDir; }
    public String getRepo() { return repo; }
    public void setRepo(String repo) { this.repo = repo; }
    public String getTag() { return tag; }
    public void setTag(String tag) { this.tag = tag; }
    public String getDataUrl() { return dataUrl; }
    public void setDataUrl(String dataUrl) { this.dataUrl = dataUrl; }
    public double getMaxAgeHours() { return maxAgeHours; }
    public void setMaxAgeHours(double maxAgeHours) { this.maxAgeHours = maxAgeHours; }
    public boolean isBootstrapEnabled() { return bootstrapEnabled; }
    public void setBootstrapEnabled(boolean bootstrapEnabled) { this.bootstrapEnabled = bootstrapEnabled; }
    public String getBootstrapFallback() { return bootstrapFallback; }
    public void setBootstrapFallback(String bootstrapFallback) { this.bootstrapFallback = bootstrapFallback; }
    public String getGithubToken() { return githubToken; }
    public void setGithubToken(String githubToken) { this.githubToken = githubToken; }
    public String getCorsOrigins() { return corsOrigins; }
    public void setCorsOrigins(String corsOrigins) { this.corsOrigins = corsOrigins; }

    public String[] corsOriginPatterns() {
        return corsOrigins == null || corsOrigins.isBlank()
                ? new String[]{"http://localhost:*", "http://127.0.0.1:*"}
                : corsOrigins.split("\\s*,\\s*");
    }
}
