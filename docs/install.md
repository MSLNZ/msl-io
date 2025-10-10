# Install

`msl-io` is available for installation via the [Python Package Index]{:target="_blank"}. It can be installed using a variety of package managers.

=== "pip"
    ```console
    pip install msl-io
    ```

=== "uv"
    ```console
    uv add msl-io
    ```

=== "poetry"
    ```console
    poetry add msl-io
    ```

=== "pdm"
    ```console
    pdm add msl-io
    ```

## Dependencies

* Python 3.9+
* [numpy]{:target="_blank"}
* [xlrd]{:target="_blank"} (bundled with `msl-io`)

### Optional Dependencies

The following packages are not automatically installed when `msl-io` is installed but may be required to read certain files

* [h5py]{:target="_blank"}
* [google-api-python-client]{:target="_blank"}
* [google-auth-httplib2]{:target="_blank"}
* [google-auth-oauthlib]{:target="_blank"}

To include [h5py]{:target="_blank"} when installing `msl-io` run


=== "pip"
    ```console
    pip install msl-io[h5py]
    ```

=== "uv"
    ```console
    uv add msl-io[h5py]
    ```

=== "poetry"
    ```console
    poetry add msl-io[h5py]
    ```

=== "pdm"
    ```console
    pdm add msl-io[h5py]
    ```

To include the Google-API packages run

=== "pip"
    ```console
    pip install msl-io[google]
    ```

=== "uv"
    ```console
    uv add msl-io[google]
    ```

=== "poetry"
    ```console
    poetry add msl-io[google]
    ```

=== "pdm"
    ```console
    pdm add msl-io[google]
    ```

[Python Package Index]: https://pypi.org/project/msl-io/
[numpy]: https://www.numpy.org/
[h5py]: https://www.h5py.org/
[xlrd]: https://xlrd.readthedocs.io/en/stable/
[google-api-python-client]: https://pypi.org/project/google-api-python-client/
[google-auth-httplib2]: https://pypi.org/project/google-auth-httplib2/
[google-auth-oauthlib]: https://pypi.org/project/google-auth-oauthlib/
