package com.beemer.bootstrap;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.DriverManager;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class MetricsImporterTest {
    @Test
    void importsParquetIntoSqlite() throws Exception {
        Path parquet = Path.of("../data/metrics.parquet");
        if (!Files.exists(parquet)) parquet = Path.of("data/metrics.parquet");
        assumeTrue(Files.exists(parquet), "metrics.parquet not present");
        Path db = Files.createTempFile("beemer-metrics", ".db");
        int n = new MetricsImporter().importParquet(db, parquet);
        assertEquals(64, n);
        try (var c = DriverManager.getConnection("jdbc:sqlite:" + db);
             var rs = c.createStatement().executeQuery("SELECT name, buffett_score FROM company_metrics WHERE symbol='INFY'")) {
            rs.next();
            assertEquals("Infosys", rs.getString(1));
            assertEquals(93.4, rs.getDouble(2), 0.05);
        }
    }
}
