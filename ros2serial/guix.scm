(use-modules 
      (guix packages)
      (guix download)
      (guix licenses)
      (gnu packages python)
      (gnu packages python-xyz)
     (guix build-system copy)
     (guix build-system pyproject)
     (gnu packages python-build)
     (gnu packages check)
     (guix build-system python)
     (th packages helix-editor))

(define hatch-reqs
(package
  (name "python-hatch-requirements-txt")
  (version "0.4.0")
  (source
   (origin
     (method url-fetch)
     (uri (pypi-uri "hatch_requirements_txt" version))
     (sha256
      (base32 "0pa5k2nrpzfi5m7a0w78f81vavf37qianbr4fdnybnc5dsa0j1c0"))))
  (build-system pyproject-build-system)
  (home-page "")
  (inputs 
     `(
      ; ("python-pytest" ,python-pytest)
      ("python-hatchling" ,python-hatchling)))
  (arguments
    ;; Broken tests or cyclic dependecies with other packages.
    '(#:phases
      (modify-phases %standard-phases
                     (delete 'sanity-check))
      #:tests? #f)) 
  (synopsis
   "Hatchling plugin to read project dependencies from requirements.txt")
  (description
   "Hatchling plugin to read project dependencies from requirements.txt")
  (license #f))
)

(define python-mpremote
(package
  (name "python-mpremote")
  (version "1.22.0")
  (source
   (origin
     (method url-fetch)
     (uri (pypi-uri "mpremote" version))
     (sha256
      (base32 "0802w0dfcwm1ykdvvnlsfd384a0ppn6dnfl83m4y1h8r52bi1pnv"))))
  (build-system pyproject-build-system)
  (home-page "")
  (inputs 
     `(
      ("python-hatch-vcs" ,python-hatch-vcs)
      ("hatch-reqs" ,hatch-reqs)
      ("python-pip" ,python-pip)
      ("python-pyserial" ,python-pyserial)
      ("python-hatchling" ,python-hatchling))) 
    (arguments
    ;; Broken tests or cyclic dependecies with other packages.
    '(#:phases
      (modify-phases %standard-phases
                     (delete 'sanity-check))
      #:tests? #f))  
  (synopsis "Tool for interacting remotely with MicroPython devices")
  (description "Tool for interacting remotely with @code{MicroPython} devices")
  (license expat)))
  
(define micropython-rp2-pico-w-stubs
  (package
    (name "python-micropython-rp2-pico-w-stubs")
    (version "1.22.1.post2")
    (source
     (origin
       (method url-fetch)
       (uri (pypi-uri "micropython_rp2_stubs" version))
       (sha256
        (base32 "0kx81xdv4aqp1bmda2s02si89wmgi0q341bfp77ycw42swhdhk3k"))))
    (build-system python-build-system)
    (inputs
      `(("python" ,python)
        ("helix-editor-bin" ,helix-editor-bin)
        ("python-lsp-server", python-lsp-server)
        ("python-mpremote" ,python-mpremote)))
     (arguments
        ; '(#:install-plan '(("./" "lib/python3.10/site-packages/micropython-rp2-pico-stubs" ))
        '(#:phases
          (modify-phases %standard-phases
            (delete 'build)
            (replace 'install ;; Replace the install step with the function defined below
               (lambda* (#:key outputs #:allow-other-keys)
                 (let* ((outlib (string-append (assoc-ref outputs "out") "/lib/python3.10/site-packages")))
               (copy-recursively "." outlib))))
            (delete 'check)
            (delete 'sanity-check))
          #:tests? #f))
     (native-search-paths
       (list (search-path-specification
            (variable "GUIX_PYTHONPATH")
            (files (list "/lib/python3.10/site-packages")))))
    (home-page "https://github.com/josverl/micropython-stubs#micropython-stubs")
    (synopsis "MicroPython stubs")
    (description "@code{MicroPython} stubs")
    (license expat))
)

(define drv-rfm69
  (package 
  (name "drv-rfm69")
  (version "0.0.1")
  (build-system copy-build-system)
  (source
     (origin
       (method url-fetch)
       (uri "https://raw.githubusercontent.com/mchobby/esp8266-upy/master/rfm69/lib/rfm69.py")
       (sha256
        (base32 "1pr318cn1l3pa470as0ah7wjz4wr3dan9nd4v83wh9c90z0qgq39"))))
  (arguments
   '(#:install-plan '(("rfm69.py" "/lib/python3.10/site-packages/rfm69.py"))))
  (native-search-paths
    (list (search-path-specification
       (variable "GUIX_PYTHONPATH")
         (files (list "/lib/python3.10/site-packages")))))
  (synopsis "")
  (description "")
  (home-page "")
  (license #f)
  )
)

(define mock-package
  (package
    (name "mock-package")
    (version "0.0.1")
    (source #f)
    (build-system copy-build-system)
    (inputs
      `(("python" ,python)
        ("helix-editor-bin" ,helix-editor-bin)
        ("python-lsp-server", python-lsp-server)
        ("python-mpremote" ,python-mpremote)
        ("drv-rfm69" ,drv-rfm69)
        ("micropython-rp2-pico-w-stubs" ,micropython-rp2-pico-w-stubs)))
    (synopsis "")
    (description "")
    (home-page "")
    (license #f)))


mock-package

