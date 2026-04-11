/**
 * File processor using DuckDB-WASM for client-side CSV to Parquet conversion
 * and automatic chunking for files exceeding the upload limit.
 */

import * as duckdb from "@duckdb/duckdb-wasm";

const CHUNK_SIZE = 4 * 1024 * 1024; // 4MB chunks (under 4.5MB limit)

let db: duckdb.AsyncDuckDB | null = null;
let initPromise: Promise<duckdb.AsyncDuckDB> | null = null;

/**
 * Initialize DuckDB-WASM (singleton)
 */
async function initDuckDB(): Promise<duckdb.AsyncDuckDB> {
  if (db) return db;
  if (initPromise) return initPromise;

  initPromise = (async () => {
    const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();

    // Select the best bundle for this browser
    const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

    const worker_url = URL.createObjectURL(
      new Blob([`importScripts("${bundle.mainWorker}");`], {
        type: "text/javascript",
      })
    );

    const worker = new Worker(worker_url);
    const logger = new duckdb.ConsoleLogger();
    db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    URL.revokeObjectURL(worker_url);

    return db;
  })();

  return initPromise;
}

export interface ChunkInfo {
  data: Blob;
  name: string;
  index: number;
  totalChunks: number;
  originalName: string;
  format: "parquet";
}

export interface ProcessedFile {
  originalName: string;
  originalSize: number;
  processedSize: number;
  format: "parquet";
  chunks: ChunkInfo[];
}

/**
 * Convert a CSV file to Parquet format using DuckDB-WASM
 */
async function csvToParquet(
  csvFile: File,
  duckDb: duckdb.AsyncDuckDB
): Promise<Uint8Array> {
  const conn = await duckDb.connect();

  try {
    // Register the CSV file with DuckDB
    const csvBuffer = await csvFile.arrayBuffer();
    await duckDb.registerFileBuffer(csvFile.name, new Uint8Array(csvBuffer));

    // Create table from CSV and export to Parquet
    const parquetName = csvFile.name.replace(".csv", ".parquet");

    await conn.query(`
      CREATE TABLE temp_data AS 
      SELECT * FROM read_csv_auto('${csvFile.name}')
    `);

    await conn.query(`
      COPY temp_data TO '${parquetName}' (FORMAT PARQUET, COMPRESSION ZSTD)
    `);

    // Get the parquet file buffer
    const parquetBuffer = await duckDb.copyFileToBuffer(parquetName);

    // Cleanup
    await conn.query("DROP TABLE IF EXISTS temp_data");
    await duckDb.dropFile(csvFile.name);
    await duckDb.dropFile(parquetName);

    return parquetBuffer;
  } finally {
    await conn.close();
  }
}

/**
 * Split a buffer into chunks of specified size
 */
function splitIntoChunks(
  data: Uint8Array,
  chunkSize: number,
  originalName: string,
  parquetName: string
): ChunkInfo[] {
  const chunks: ChunkInfo[] = [];
  let offset = 0;
  const totalChunks = Math.ceil(data.length / chunkSize);

  while (offset < data.length) {
    const end = Math.min(offset + chunkSize, data.length);
    const chunkData = data.slice(offset, end);
    const index = chunks.length;

    chunks.push({
      data: new Blob([chunkData], { type: "application/octet-stream" }),
      name: totalChunks > 1 ? `${parquetName}.${String(index).zfill(3)}` : parquetName,
      index,
      totalChunks,
      originalName,
      format: "parquet",
    });

    offset = end;
  }

  return chunks;
}

// Polyfill for String.prototype.zfill
declare global {
  interface String {
    zfill(width: number): string;
  }
}

String.prototype.zfill = function (width: number): string {
  return this.padStart(width, "0");
};

/**
 * Process a single CSV file: convert to Parquet and split into chunks if needed
 */
async function processFile(
  file: File,
  duckDb: duckdb.AsyncDuckDB
): Promise<ProcessedFile> {
  // Convert CSV to Parquet
  const parquetData = await csvToParquet(file, duckDb);

  // Split into chunks if needed
  const parquetName = file.name.replace(".csv", ".parquet");
  const chunks = splitIntoChunks(parquetData, CHUNK_SIZE, file.name, parquetName);

  return {
    originalName: file.name,
    originalSize: file.size,
    processedSize: parquetData.length,
    format: "parquet",
    chunks,
  };
}

/**
 * Process multiple CSV files with progress callback
 */
export async function processFiles(
  files: File[],
  onProgress?: (
    currentFile: number,
    totalFiles: number,
    fileName: string,
    status: string
  ) => void
): Promise<ProcessedFile[]> {
  const results: ProcessedFile[] = [];

  // Initialize DuckDB
  onProgress?.(0, files.length, "", "Initializing DuckDB...");
  const duckDb = await initDuckDB();

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    onProgress?.(i, files.length, file.name, "Converting to Parquet...");

    const result = await processFile(file, duckDb);
    results.push(result);

    onProgress?.(i + 1, files.length, file.name, "Complete");
  }

  return results;
}

/**
 * Format bytes as human-readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
