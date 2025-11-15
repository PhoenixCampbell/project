const express = require("express");
require("dotenv").config();
const path = require("path");

const app = express();
const port = 3000;

const clientId = process.env.CLIENT_ID;
const clientSecret = process.env.CLIENT_SECRET;

const redirectUri = "http://localhost:3000/auth/callback";
const tenant = "common";

app.use(express.static(__dirname));

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

app.get("/auth/callback", async (req, res) => {
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

app.listen(port, () => {
  console.log(`Server running → http://localhost:${port}`);
});