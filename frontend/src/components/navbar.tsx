"use client";

import Image from "next/image";

export default function Navbar() {
  return (
    <nav className="mb-6 flex items-center">
      <Image
        src="/_logo.png"
        alt="Greenwood Technologies Logo"
        width={60}
        height={60}
        className="mr-4"
      />
      <h1 className="text-2xl font-bold">Greenwood Technologies</h1>
    </nav>
  );
}
