package com.beemer.api;

public class NoDataException extends RuntimeException {
    public NoDataException() { super("Data is loading. Back in a few minutes."); }
}
