#!/usr/bin/env bash
curl -s --unix-socket /run/realty/realty.sock http://localhost/complexes/ > /tmp/complexes.html
