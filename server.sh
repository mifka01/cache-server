if [[ -n "$1" ]]; then
  export XDG_CONFIG_HOME="$(pwd)/tmp/configs/$1"
  shift
fi

python3 -m cache_server_app.main "$@"
