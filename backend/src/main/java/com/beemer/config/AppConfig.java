package com.beemer.config;

import com.beemer.bootstrap.DataBootstrap;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.zaxxer.hikari.HikariDataSource;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.cache.CacheManager;
import org.springframework.cache.caffeine.CaffeineCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import javax.sql.DataSource;
import java.time.Duration;

@Configuration
public class AppConfig {
    @Bean
    public DataSource dataSource(BeemerProperties props) throws Exception {
        if (props.isBootstrapEnabled()) new DataBootstrap(props).ensure();
        HikariDataSource ds = new HikariDataSource();
        ds.setPoolName("beemer");
        ds.setDriverClassName("org.sqlite.JDBC");
        ds.setJdbcUrl("jdbc:sqlite:" + props.dbFile());
        ds.setMaximumPoolSize(4);
        ds.setConnectionInitSql("PRAGMA busy_timeout=5000");
        return ds;
    }

    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager manager = new CaffeineCacheManager("cockpit", "company", "companies", "picks", "metrics", "screener", "prices", "academy");
        manager.setCaffeine(Caffeine.newBuilder().expireAfterWrite(Duration.ofMinutes(10)));
        return manager;
    }

    @Bean
    public WebMvcConfigurer cors(BeemerProperties props) {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOriginPatterns(props.corsOriginPatterns())
                        .allowedMethods("GET", "POST", "OPTIONS")
                        .allowedHeaders("*");
            }
        };
    }

    @Bean
    public OpenAPI openAPI() {
        return new OpenAPI().info(new Info()
                .title("Beemer API")
                .version("1.0")
                .description("Precision research for India's tech stocks. Educational only — not investment advice."));
    }
}
