module.exports = {
  apps: [
    {
      name: "caregist-api",
      script: "/home/ubuntu/caregist/.venv/bin/uvicorn",
      args: "api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*",
      cwd: "/home/ubuntu/caregist",
      interpreter: "none",
      env_file: "/home/ubuntu/caregist/.env",
      env: {
        PYTHONPATH: "/home/ubuntu/caregist",
      },
      restart_delay: 1000,
      min_uptime: "10s",
      kill_timeout: 10000,
      max_restarts: 10,
      max_memory_restart: "512M",
      autorestart: true,
      watch: false,
      time: true,
      out_file: "/home/ubuntu/caregist/logs/pm2-out.log",
      error_file: "/home/ubuntu/caregist/logs/pm2-error.log",
    },
  ],
};
