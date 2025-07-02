"use client";

import Image from "next/image";

export default function Navbar() {
  return (
    <nav className="flex flex-col items-center">
      <Image
        src="/fb_logo.png"
        alt="Fibrolytix Bio Logo"
        width={300}
        height={60}
      />
      <h1 className="text-2xl my-6 font-bold text-center">
        Cardiac Fibrosis Compound Selection System Demo
      </h1>
    </nav>
  );
}