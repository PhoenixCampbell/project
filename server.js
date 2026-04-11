/* eslint-env node, es2021 */
import express from "express";
import dotenv from "dotenv";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { spawn } from "child_process";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const app = express();
const PORT = process.env.PORT || 3000;

const clientId = process.env.CLIENT_ID;
const clientSecret = process.env.CLIENT_SECRET;

const redirectUri = "http://localhost:3000/auth/callback";
const tenant = "common";

app.use(express.json());
app.use(express.static(__dirname));

const dataDir = path.join(__dirname, process.env.DATA_DIR || "data");

if (process.env.NODE_ENV !== "test") {
	app.listen(PORT, () => {
		console.log(`Server running → http://localhost:${PORT}`);
	});
}
const tenureFilePath = path.join(dataDir, "tenure.csv");

if (!fs.existsSync(dataDir)) {
	fs.mkdirSync(dataDir);
}
//-------------------------------------------------------------------------
//TODO dont let professors change their email or ID to someone else / verify that its their info
//  -shove their email into facultyId and disable switching
//  -verify that it is a @dsu.edu email path
//TODO Professors should only have to rate courses they would teach anyway, not random things
//  -dropdown multiple checklist so profs in each college only has to rate classes in their college
//  -ie Beacom - MATH,CSC,CSI etc
//  -use class info for filter, then only show through that filter
//-------------------------------------------------------------------------
const solutionFilePath = path.join(dataDir, "solution.xlsx");

app.get("/login", (req, res) => {
	const url =
		`https://login.microsoftonline.com/${tenant}/oauth2/v2.0/authorize` +
		`?client_id=${clientId}` +
		`&response_type=code` +
		`&redirect_uri=${encodeURIComponent(redirectUri)}` +
		`&response_mode=query` +
		`&scope=openid profile email`;

	res.redirect(url);
});
//connect to faculty.html
app.get("/faculty", (req, res) => {
	res.sendFile(path.join(__dirname, "faculty.html"));
});

function runSolverScript(termCode) {
	return new Promise((resolve, reject) => {
		const solverPath = path.join(__dirname, "solver.py");

		if (!fs.existsSync(solverPath)) {
			return reject(
				new Error(
					`Solver script not found at ${solverPath}. Ask Ryan or IT.`
				)
			);
		}

		//change "python3" to "python" or vice versa if needed for environment
		const pythonCMD = process.env.PYTHON || "python";

		const args = [solverPath];
		if (termCode) {
			args.push(termCode);
		}

		const proc = spawn(pythonCMD, args, {
			cwd: __dirname,
		});

		let stdout = "";
		let stderr = "";

		proc.stdout.on("data", (chunk) => {
			stdout += chunk.toString();
		});

		proc.stderr.on("data", (chunk) => {
			stderr += chunk.toString();
		});

		proc.on("error", (err) => {
			reject(err);
		});

		proc.on("close", (code) => {
			if (code === 0) {
				resolve({ stdout, stderr, code });
			} else {
				const err = new Error(
					`Solver exited with code ${code}${
						stderr ? `: ${stderr}` : ""
					}`
				);
				err.code = code;
				err.stdout = stdout;
				err.stderr = stderr;
				reject(err);
			}
		});
	});
}
//if preference for term exists, add to it
function appendSubmittedPreference(pref) {
	const {
		facultyId,
		termCode,
		termLabel,
		classId,
		classLabel,
		rating,
		desireRating,
	} = pref;
	if (!facultyId || !termCode || !classId) {
		throw new Error("Missing facultyId, termCode, or classId");
	}

	//Sanitize data for filesystem (specifically any crazy user names)
	const safeFaculty = String(facultyId)
		.trim()
		.toLowerCase()
		.replace(/[^a-z0-9@._-]/gi, "_")
		.replace(/[@.]/g, "_");

	const fileName = `pref_${safeFaculty}_${termCode}.csv`; //connect and name appropriately the file
	const filePath = path.join(dataDir, fileName); // shove to proper folder

	const header =
		"timestamp,facultyId,termCode,termLabel,classId,classLabel,rating,desireRating";

	const scrub = (v) =>
		String(v ?? "")
			.replace(/,/g, " ")
			.replace(/\r?\n/g, " ");

	const timestamp = new Date()
		.toISOString()
		.replace("T", " ")
		.substring(0, 19);

	const newRow = [
		scrub(timestamp),
		scrub(facultyId),
		scrub(termCode),
		scrub(termLabel),
		scrub(classId),
		scrub(classLabel),
		Number.isFinite(Number(rating)) ? Number(rating) : "",
		Number.isFinite(Number(desireRating)) ? Number(desireRating) : "",
	].join(",");

	if (!fs.existsSync(filePath)) {
		const content = header + "\n" + newRow + "\n";
		fs.writeFileSync(filePath, content, "utf8"); //header labels
		return;
	}

	//file exists -> read and update/replace
	const raw = fs.readFileSync(filePath, "utf8");
	const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);

	const dataLines = [];
	for (const line of lines) {
		if (line.trim() === header) continue;
		const cols = line.split(",");
		if (cols.length < 8) continue;
		dataLines.push(line);
	}

	const filtered = [];

	for (const line of dataLines) {
		const cols = line.split(",");
		const existingTermCode = cols[2] ?? "";
		const existingClassId = cols[4] ?? "";

		// if same termCode + classId, drop old row
		if (
			existingTermCode === String(termCode) &&
			existingClassId === String(classId)
		) {
			continue;
		}
		filtered.push(line);
	}

	filtered.push(newRow);

	//Rewrite entire file: header + all rows
	const output = header + "\n" + filtered.join("\n") + "\n";
	fs.writeFileSync(filePath, output, "utf8");
}

function loadTenureMap() {
	const map = {};
	if (!fs.existsSync(tenureFilePath)) return map;

	const raw = fs.readFileSync(tenureFilePath, "utf8");
	const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);

	for (let i = 1; i < lines.length; i++) {
		const [facultyKey, tenureStr] = lines[i].split(",");
		if (!facultyKey) continue;
		const t = parseInt(tenureStr, 10);
		if (!Number.isNaN(t)) {
			map[facultyKey] = t;
		}
	}
	return map;
}

function saveTenureMap(map) {
	const header = "facultyKey,tenure";
	const lines = [header];
	for (const [key, tenure] of Object.entries(map)) {
		lines.push(`${key},${tenure}`);
	}
	fs.writeFileSync(tenureFilePath, lines.join("\n") + "\n", "utf8");
}

function getFacultyKeysFromPrefs(termCode = null) {
	const files = fs
		.readdirSync(dataDir)
		.filter((f) => f.startsWith("pref_") && f.endsWith(".csv"));
	const keys = new Set();

	for (const filename of files) {
		const stem = filename.replace(".csv", "");
		const withoutPrefix = stem.substring(5);
		const parts = withoutPrefix.split("_");
		if (parts.length < 2) continue;

		const fileTerm = parts[parts.length - 1];
		if (termCode && fileTerm !== String(termCode)) continue;

		const facultyKey = parts.slice(0, parts.length - 1).join("_");
		keys.add(facultyKey);
	}

	return Array.from(keys);
}

function displayNameFromFacultyKey(facultyKey) {
	const parts = facultyKey.split("_");
	const dsuIndex = parts.indexOf("dsu");
	const nameParts = dsuIndex > 0 ? parts.slice(0, dsuIndex) : parts;

	return nameParts
		.map((p) => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase())
		.join(" ");
}

app.post("/api/preferences/submit", (req, res) => {
	const body = req.body || {};
	const {
		facultyId,
		termCode,
		termLabel,
		classId,
		classLabel,
		rating,
		desireRating,
	} = body;

	if (
		!facultyId ||
		!termCode ||
		!classId ||
		rating === undefined ||
		rating === null ||
		desireRating === undefined ||
		desireRating === null
	) {
		return res.status(400).json({
			message:
				"Missing required fields (facultyId, term, class, rating).",
		});
	}

	const rNum = Number(rating);
	if (!Number.isInteger(rNum) || rNum < 0 || rNum > 4) {
		return res.status(400).json({
			message: "Rating must be an integer between 0 and 4",
		});
	}

	try {
		appendSubmittedPreference({
			facultyId,
			termCode,
			termLabel: termLabel || "",
			classId,
			classLabel: classLabel || "",
			rating: rNum,
			desireRating,
		});

		return res.json({
			message: "Preference saved and submitted successfully.",
		});
	} catch (err) {
		console.error("Error submitting preference:", err);
		return res.status(500).json({
			message: "Server error while submiting preference.",
		});
	}
});

app.get("/getNames", (req, res) => {
	fs.readdir(dataDir, (err, files) => {
		if (err) {
			return res
				.status(500)
				.json({ error: "Could not read data directory" });
		}

		// Only .csv files
		const csvFiles = files.filter((f) => f.endsWith(".csv"));

		const names = csvFiles.map((filename) => {
			const raw = filename.replace(".csv", "");

			// Split by underscores
			const parts = raw.split("_");
			// Expected pattern:
			// pref_<first>_<last...>_dsu_edu_<date>

			// Find "dsu" which marks the end of the name section
			const dsuIndex = parts.indexOf("dsu");

			// Name is everything from index 1 up to "dsu"
			// Example: ["pref","phoenix","campbell","dsu","edu","202510"]
			let nameParts;

			if (dsuIndex > 1) {
				nameParts = parts.slice(1, dsuIndex); // Could be ["mary","ann","smith"]
			} else {
				// Fallback: just use everything except pref and date
				nameParts = parts.slice(1, parts.length - 1);
			}

			// Capitalize each part
			const formattedName = nameParts
				.map(
					(part) =>
						part.charAt(0).toUpperCase() +
						part.slice(1).toLowerCase()
				)
				.join(" ");

			return formattedName;
		});

		// Remove duplicates and sort alphabetically
		const uniqueSortedNames = [...new Set(names)].sort((a, b) =>
			a.localeCompare(b)
		);

		res.json(uniqueSortedNames);
	});
});

app.get("/api/admin/tenure/list", (req, res) => {
	try {
		const tenureMap = loadTenureMap();
		const facultyKeys = getFacultyKeysFromPrefs();

		const items = facultyKeys.map((key) => ({
			facultyKey: key,
			displayName: displayNameFromFacultyKey(key),
			tenure: tenureMap[key] ?? null,
		}));

		items.sort((a, b) => a.displayName.localeCompare(b.displayName));

		res.json(items);
	} catch (err) {
		console.error("Error listing tenure:", err);
		res.status(500).json({ error: "Failed to list tenure data" });
	}
});

// prettier-ignore
app.post("/api/admin/solve", async(req, res) => {
	try {
        const { termCode } = req.body || {};

        if (!termCode) {
            return res.status(400).json({
                success: false,
                message: "termCode is required to run solver",
            });
        }

        const tenureMap = loadTenureMap();
        const facultyKeys = getFacultyKeysFromPrefs(termCode);
        const missing = facultyKeys.filter((k) => tenureMap[k] == null);

        if (missing.length > 0) {
            const name = missing.map(displayNameFromFacultyKey);
            return res.status(400).json({
                success: false,
                message: "Connot run solver. Tenure must be assigned for: " + names.join(", "),
            });
        }

        const result = await runSolverScript(termCode);

		//make sure the file actually exists
		const solutionExists = fs.existsSync(solutionFilePath);

		return res.json({
			success: true,
			message: solutionExists
				? `Solver completed and solution.xlsx was generated for term ${termCode}.`
				: `Solver completed for term ${termCode}, but solution.xlsx was not found. Check solver script output.`,
			stdout: result.stdout,
			stderr: result.stderr,
		});
	} catch (err) {
		console.error("Error running solver:", err);
		return res.status(500).json({
			success: false,
			message: err.message || "Error running solver script.",
		});
	}
});

app.get("/api/admin/solution/status", (req, res) => {
	const exists = fs.existsSync(solutionFilePath);
	return res.json({ exists });
});

app.get("api/admin/solution/download", (req, res) => {
	if (!fs.existsSync(solutionFilePath)) {
		return res
			.status(404)
			.send("solution.xlsx not found. Run the solver first.");
	}
	res.download(solutionFilePath, "solution.xlsx");
});

// prettier-ignore
app.get("/auth/callback", async(req, res) => {
	const code = req.query.code;

	const tokenResponse = await fetch(
		`https://login.microsoftonline.com/${tenant}/oauth2/v2.0/token`,
		{
			method: "POST",
			headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({
				client_id: clientId,
				client_secret: clientSecret,
				grant_type: "authorization_code",
				code,
				redirect_uri: redirectUri,
			}),
		}
	);

	const tokenData = await tokenResponse.json();
	res.send(tokenData);
});

app.post("/api/admin/tenure/save", (req, res) => {
	const { facultyKey, tenure } = req.body || {};
	if (!facultyKey) {
		return res
			.status(400)
			.json({ success: false, message: "facultyKey is required" });
	}
	const tNum = parseInt(tenure, 10);
	if (Number.isNaN(tNum) || tNum < 0) {
		return res.status(400).json({
			success: false,
			message: "Tenure must be a non-negitive integer.",
		});
	}

	try {
		const tenureMap = loadTenureMap();
		tenureMap[facultyKey] = tNum;
		saveTenureMap(tenureMap);
		return res.json({ success: true, message: "Tenure saved" });
	} catch (err) {
		console.error("Error saving tenure:", err);
		return res.status(500).json({
			success: false,
			message: "Server error while saving tenure",
		});
	}
});

// POST endpoint that calls Python
app.post("/downloadFile", (req, res) => {
	const { name } = req.body;
	if (!name) return res.status(400).send("Name not provided");

	// Call Python script with the name as an argument
	const py = spawn("python3", ["preferences.py", name]);

	let output = "";
	let errorOutput = "";

	py.stdout.on("data", (data) => {
		output += data.toString();
	});

	py.stderr.on("data", (data) => {
		errorOutput += data.toString();
	});

	py.on("close", (code) => {
		if (code !== 0) {
			console.error("Python error:", errorOutput);
			return res.status(500).send("Python script error");
		}

		// Use Python output as file content
		res.setHeader(
			"Content-Disposition",
			`attachment; filename="${name}_file.txt"`
		);
		res.setHeader("Content-Type", "text/plain");
		res.send(output);
	});
});
