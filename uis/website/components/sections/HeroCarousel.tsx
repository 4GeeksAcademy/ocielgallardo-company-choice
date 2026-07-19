"use client";

import { useEffect, useState } from "react";

const HERO_IMAGES = [
  "/images/hero/hero-001.png",
  "/images/hero/hero-002.jpg",
  "/images/hero/hero-003.jpg",
  "/images/hero/hero-004.webp",
] as const;

export function HeroCarousel() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setIndex((current) => (current + 1) % HERO_IMAGES.length);
    }, 10_000);

    return () => window.clearInterval(id);
  }, []);

  return (
    <div aria-hidden className="hero-carousel">
      <div
        className="hero-carousel-track"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {HERO_IMAGES.map((src) => (
          <div key={src} className="hero-carousel-slide">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={src}
              alt=""
              className={
                src.includes("hero-002")
                  ? "hero-carousel-image hero-carousel-image--top"
                  : "hero-carousel-image"
              }
            />
          </div>
        ))}
      </div>
    </div>
  );
}
