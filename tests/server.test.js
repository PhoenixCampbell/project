// Ensure server does NOT start listening and set env first
process.env.NODE_ENV = "test";
process.env.DATA_DIR = "data_test"; // <-- must be set BEFORE importing server

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import request from "supertest";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Make test read the SAME folder the server writes to
const dataDir = path.join(path.resolve(__dirname, ".."), process.env.DATA_DIR);

let app;

beforeAll(async() => {
  // dynamic import ensures env vars are set before server runs
  ({ app } = await import("../server.js"));

  // ensure test-specific data directory exists
  if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir);
});

afterAll(() => {
  // cleanup all files created during tests
  if (fs.existsSync(dataDir)) {
    const files = fs.readdirSync(dataDir);
    for (const f of files) fs.unlinkSync(path.join(dataDir, f));
    fs.rmdirSync(dataDir);
  }
});

describe("Server routes", () => {
  test("GET /faculty returns faculty.html", async() => {
    const res = await request(app).get("/faculty");
    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/html/);
  });

  test("GET /login redirects to Microsoft login", async() => {
    const res = await request(app).get("/login");
    expect(res.status).toBe(302);
    expect(res.headers.location).toMatch(/login.microsoftonline.com/);
  });

  test("POST /api/preferences/submit saves a preference", async() => {
    const pref = {
      facultyId: "john.doe@dsu.edu",
      termCode: "20251",
      termLabel: "Spring 2025",
      classId: "C101",
      classLabel: "Math 101",
      rating: 3,
      desireRating: 2,
    };

    const res = await request(app).post("/api/preferences/submit").send(pref);

    expect(res.status).toBe(200);
    expect(res.body.message).toMatch(/Preference saved/);

    const files = fs.readdirSync(dataDir);
    console.log("Files in data_test:", files);
    expect(files.some((f) => f.includes("john_doe"))).toBe(true);
  });

  test("POST /api/preferences/submit fails for missing fields", async() => {
    const res = await request(app).post("/api/preferences/submit").send({ facultyId: "x" });

    expect(res.status).toBe(400);
    expect(res.body.message).toMatch(/Missing required fields/);
  });
});
