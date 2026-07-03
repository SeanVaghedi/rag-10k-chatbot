/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    // pdfjs-dist references an optional Node "canvas" module that isn't needed
    // in the browser; prevent webpack from trying to resolve/bundle it.
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
