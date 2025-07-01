"use client";

import Image from "next/image";

export default function Navbar() {
  return (
    <nav className="mb-6 flex items-center">
      <Image
        src="/fb_logo.png"
        alt="Fibrolytix Bio Logo"
        width={230}
        height={60}
      />
      <h1 className="text-2xl font-bold mx-4">X</h1>
      <Image
        src="/gt_logo.png"
        alt="Greenwood Technologies Logo"
        width={60}
        height={60}
        className="mr-2"
      />
      <h1 className="text-2xl font-bold">Greenwood Technologies</h1>
    </nav>
  );
}
