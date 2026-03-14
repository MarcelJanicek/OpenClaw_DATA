import express from 'express';
import multer from 'multer';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import fs from 'fs';
import morgan from 'morgan';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Directories
const TMP_DIR = path.join(__dirname, 'tmp');
const OUTPUT_DIR = path.join(__dirname, '..', 'compliance-agent', 'outputs');
fs.mkdirSync(OUTPUT_DIR, { recursive: true });
const SCRIPT_PATH = path.join(__dirname, '..', 'compliance-agent', 'scripts', 'run_doc_review.sh');
const RULES_PATH = path.join(__dirname, '..', 'rules', 'entity_profile.min.yaml');

// Ensure tmp directory exists
fs.mkdirSync(TMP_DIR, { recursive: true });

const app = express();
app.use(morgan('dev'));

// In-memory job tracking
const jobs = new Map();

/**
 * Multer configuration
 */
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, TMP_DIR);
  },
  filename: function (req, file, cb) {
    // keep original name
    cb(null, file.originalname);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50 MB
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (ext !== '.docx') {
      return cb(new Error('Only .docx files are allowed'));
    }
    cb(null, true);
  }
}).single('file');

// POST /upload
app.post('/upload', (req, res) => {
  upload(req, res, err => {
    if (err) {
      return res.status(400).json({ error: err.message });
    }

    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const uploadedPath = req.file.path; // absolute path in tmp/
    const basename = path.parse(req.file.originalname).name; // without extension

    // Spawn the compliance script
    const child = spawn(SCRIPT_PATH, [uploadedPath, RULES_PATH, `outputs/${basename}`]);

    const jobId = `${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
    jobs.set(jobId, {
      status: 'running',
      basename,
      outputFile: `${basename}.commented.docx`
    });

    // Capture stdout to extract job id if script outputs one
    let stdoutData = '';
    child.stdout.on('data', chunk => {
      stdoutData += chunk.toString();
    });

    child.on('close', code => {
      const job = jobs.get(jobId);
      if (!job) return;

      if (code === 0) {
        job.status = 'complete';
      } else {
        job.status = 'error';
        job.error = `Process exited with code ${code}`;
      }
      // Try to overwrite jobId if script provided one (first token in stdout)
      const scriptJobId = stdoutData.trim().split(/\s+/)[0];
      if (scriptJobId) {
        job.scriptJobId = scriptJobId;
      }
    });

    child.on('error', procErr => {
      const job = jobs.get(jobId);
      if (job) {
        job.status = 'error';
        job.error = procErr.message;
      }
    });

    // Immediately respond
    res.json({ jobId });
  });
});

// GET /status/:jobId
app.get('/status/:jobId', (req, res) => {
  const { jobId } = req.params;
  const job = jobs.get(jobId);
  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }
  if (job.status === 'complete') {
    return res.json({ status: job.status, outputUrl: `/download/${job.outputFile}` });
  } else if (job.status === 'error') {
    return res.json({ status: job.status, error: job.error || 'Unknown error' });
  } else {
    return res.json({ status: job.status });
  }
});

// GET /download/:filename
app.get('/download/:filename', (req, res) => {
  const { filename } = req.params;
  const filePath = path.join(OUTPUT_DIR, filename);
  fs.access(filePath, fs.constants.R_OK, err => {
    if (err) {
      return res.status(404).json({ error: 'File not found or not ready' });
    }
    res.download(filePath);
  });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
