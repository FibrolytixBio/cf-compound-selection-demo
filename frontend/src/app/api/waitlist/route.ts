import { NextRequest, NextResponse } from "next/server";

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_TABLE_NAME = process.env.AIRTABLE_TABLE_NAME || "waitlist";

export async function POST(request: NextRequest) {
  try {
    const { email, timestamp, source } = await request.json();

    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Valid email is required" },
        { status: 400 }
      );
    }

    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      console.error("Missing Airtable configuration");
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    // Debug logging
    console.log("Attempting to submit to Airtable:");
    console.log("Base ID:", AIRTABLE_BASE_ID);
    console.log("Table Name:", AIRTABLE_TABLE_NAME);
    console.log(
      "URL:",
      `https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_TABLE_NAME}`
    );

    // Submit to Airtable
    const airtableResponse = await fetch(
      `https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_TABLE_NAME}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${AIRTABLE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          fields: {
            Email: email,
            Timestamp: timestamp,
            Source: source,
            Select: "New",
          },
        }),
      }
    );

    if (!airtableResponse.ok) {
      const errorData = await airtableResponse.text();
      console.error("Airtable error:", errorData);
      throw new Error("Failed to save to Airtable");
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Waitlist submission error:", error);
    return NextResponse.json(
      { error: "Failed to submit to waitlist" },
      { status: 500 }
    );
  }
}
